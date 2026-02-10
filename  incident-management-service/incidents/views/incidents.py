import json
import uuid
import os
from datetime import datetime, timezone
from urllib import request as urlrequest
from urllib.error import URLError

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from sqlalchemy import select

from ..metrics import INCIDENTS_TOTAL, INCIDENT_MTTA_SECONDS, INCIDENT_MTTR_SECONDS

from ..db import get_session_factory, init_models
from ..models import Incident


def _incident_to_dict(incident: Incident) -> dict:
    def dt(value: datetime | None):
        return value.isoformat().replace("+00:00", "Z") if value else None

    return {
        "id": str(incident.id),
        "service": incident.service,
        "severity": incident.severity,
        "title": incident.title,
        "status": incident.status,
        "created_at": dt(incident.created_at),
        "acknowledged_at": dt(incident.acknowledged_at),
        "resolved_at": dt(incident.resolved_at),
    }


@csrf_exempt
@require_http_methods(["GET", "POST"])
def incidents_collection(request):
    init_models()
    SessionLocal = get_session_factory()

    if request.method == "GET":
        status_filter = request.GET.get("status")
        severity_filter = request.GET.get("severity")
        service_filter = request.GET.get("service")

        with SessionLocal() as session:
            stmt = select(Incident)
            if status_filter:
                stmt = stmt.where(Incident.status == str(status_filter))
            if severity_filter:
                stmt = stmt.where(Incident.severity == str(severity_filter))
            if service_filter:
                stmt = stmt.where(Incident.service == str(service_filter))

            incidents = session.execute(stmt.order_by(Incident.created_at.desc()).limit(100)).scalars().all()
            return JsonResponse({"items": [_incident_to_dict(i) for i in incidents]}, status=200)

    try:
        body = json.loads((request.body or b"{}").decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    service = body.get("service")
    severity = body.get("severity")
    title = body.get("title") or body.get("message")

    if not service or not severity or not title:
        return JsonResponse({"error": "missing_fields", "required": ["service", "severity", "title"]}, status=400)

    incident = Incident(service=str(service), severity=str(severity), title=str(title), status="open")
    with SessionLocal() as session:
        session.add(incident)
        session.commit()
        session.refresh(incident)

    INCIDENTS_TOTAL.labels(status="open").inc()

    # Best-effort: call On-Call + Notification services (skeleton).
    oncall_base = os.environ.get("ONCALL_BASE_URL", "http://oncall:8000")
    notification_base = os.environ.get("NOTIFICATION_BASE_URL", "http://notification:8000")
    try:
        team = str(service)
        urlrequest.urlopen(
            urlrequest.Request(f"{oncall_base}/api/v1/oncall/current?team={team}", method="GET"),
            timeout=1.5,
        ).read()
    except Exception:
        pass
    try:
        payload = json.dumps({"incident_id": str(incident.id), "message": str(title), "channel": "mock"}).encode("utf-8")
        urlrequest.urlopen(
            urlrequest.Request(
                f"{notification_base}/api/v1/notify",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            ),
            timeout=1.5,
        ).read()
    except Exception:
        pass

    return JsonResponse(_incident_to_dict(incident), status=201)


@csrf_exempt
@require_http_methods(["GET", "PATCH"])
def incident_detail(request, incident_id: uuid.UUID):
    init_models()
    SessionLocal = get_session_factory()

    with SessionLocal() as session:
        incident = session.get(Incident, incident_id)
        if incident is None:
            return JsonResponse({"error": "not_found"}, status=404)

        if request.method == "GET":
            return JsonResponse(_incident_to_dict(incident), status=200)

        try:
            body = json.loads((request.body or b"{}").decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid_json"}, status=400)

        status_value = body.get("status")
        if status_value:
            new_status = str(status_value)
            incident.status = new_status

            now = datetime.now(timezone.utc)

            if incident.status == "acknowledged" and incident.acknowledged_at is None:
                incident.acknowledged_at = now
                # Observe MTTA.
                try:
                    mtta = (incident.acknowledged_at - incident.created_at).total_seconds()
                    if mtta >= 0:
                        INCIDENT_MTTA_SECONDS.observe(mtta)
                except Exception:
                    pass
            if incident.status == "resolved" and incident.resolved_at is None:
                incident.resolved_at = now
                # Observe MTTR.
                try:
                    mttr = (incident.resolved_at - incident.created_at).total_seconds()
                    if mttr >= 0:
                        INCIDENT_MTTR_SECONDS.observe(mttr)
                except Exception:
                    pass

            if new_status in {"open", "acknowledged", "in_progress", "resolved"}:
                INCIDENTS_TOTAL.labels(status=new_status).inc()

        session.add(incident)
        session.commit()
        session.refresh(incident)

        return JsonResponse(_incident_to_dict(incident), status=200)


@require_http_methods(["GET"])
def incident_metrics(request, incident_id: uuid.UUID):
    init_models()
    SessionLocal = get_session_factory()

    with SessionLocal() as session:
        incident = session.get(Incident, incident_id)
        if incident is None:
            return JsonResponse({"error": "not_found"}, status=404)

        def secs(a: datetime | None, b: datetime | None):
            if not a or not b:
                return None
            try:
                return max(0.0, (a - b).total_seconds())
            except Exception:
                return None

        return JsonResponse(
            {
                "id": str(incident.id),
                "mtta_seconds": secs(incident.acknowledged_at, incident.created_at),
                "mttr_seconds": secs(incident.resolved_at, incident.created_at),
                "status": incident.status,
            },
            status=200,
        )

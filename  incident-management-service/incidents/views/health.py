from django.http import JsonResponse
from sqlalchemy import text

from ..db import get_engine, init_models


def health_view(request):
    try:
        init_models()
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return JsonResponse({"status": "ok"}, status=200)
    except Exception as exc:
        return JsonResponse({"status": "error", "error": str(exc)}, status=503)

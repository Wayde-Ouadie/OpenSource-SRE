from django.urls import path

from incidents.views import health, metrics, incidents


urlpatterns = [
    path("health", health.health_view, name="health"),
    path("metrics", metrics.metrics_view, name="metrics"),
    path("api/v1/incidents", incidents.incidents_collection, name="incidents_collection"),
    path("api/v1/incidents/<uuid:incident_id>/metrics", incidents.incident_metrics, name="incident_metrics"),
    path("api/v1/incidents/<uuid:incident_id>", incidents.incident_detail, name="incident_detail"),
]

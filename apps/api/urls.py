from django.urls import path

from apps.api.views import evaluate_session, get_session

app_name = "api"

urlpatterns = [
    path("sessions/<int:session_id>/", get_session, name="get_session"),
    path("sessions/<int:session_id>/evaluate/", evaluate_session, name="evaluate_session"),
]

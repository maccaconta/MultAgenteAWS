from django.urls import path
from apps.realtime.consumers import SimulationConsumer

websocket_urlpatterns = [
    path("ws/simulations/<int:session_id>/", SimulationConsumer.as_asgi()),
]
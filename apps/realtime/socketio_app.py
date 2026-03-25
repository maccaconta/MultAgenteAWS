from __future__ import annotations

"""
Adaptador opcional para clientes Socket.IO.

Recomendação principal do projeto: usar Django Channels para WebSocket nativo.
Este módulo existe apenas se o front-end exigir protocolo Socket.IO.
"""

import socketio
from django.core.asgi import get_asgi_application

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
django_asgi_app = get_asgi_application()
application = socketio.ASGIApp(socketio_server=sio, other_asgi_app=django_asgi_app)

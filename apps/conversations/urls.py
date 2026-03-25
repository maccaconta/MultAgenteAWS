from django.urls import path

from apps.conversations.views import ConversationRoomView

urlpatterns = [
    path('<int:session_id>/', ConversationRoomView.as_view(), name='conversation-room'),
]

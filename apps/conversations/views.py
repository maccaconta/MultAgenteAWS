from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.conversations.selectors import ConversationSelector


class ConversationRoomView(LoginRequiredMixin, TemplateView):
    template_name = 'conversations/room.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['session'] = ConversationSelector.session_detail(kwargs['session_id'], self.request.user.id)
        return context

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import FormView, TemplateView

from apps.catalog.forms import SimulationLaunchForm
from apps.catalog.selectors import CatalogSelector
from apps.conversations.services import ConversationSessionService


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'catalog/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['blueprints'] = CatalogSelector.active_blueprints()
        context['personas'] = CatalogSelector.active_components('persona')
        context['scenarios'] = CatalogSelector.active_components('scenario')
        context['specialties'] = CatalogSelector.active_components('specialty')
        context['launch_form'] = SimulationLaunchForm()
        return context


class LaunchSimulationView(LoginRequiredMixin, FormView):
    form_class = SimulationLaunchForm
    template_name = 'catalog/dashboard.html'

    def form_valid(self, form):
        session = ConversationSessionService.create_session_from_form(self.request.user, form.cleaned_data)
        return redirect('conversation-room', session_id=session.pk)

from django.urls import path

from apps.catalog.views import DashboardView, LaunchSimulationView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('launch/', LaunchSimulationView.as_view(), name='launch-simulation'),
]

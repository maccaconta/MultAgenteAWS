from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('apps.catalog.urls')),
    path('conversations/', include('apps.conversations.urls')),
    path('api/', include('apps.api.urls')),
]

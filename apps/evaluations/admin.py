from django.contrib import admin

from apps.evaluations.models import EvaluationSnapshot


@admin.register(EvaluationSnapshot)
class EvaluationSnapshotAdmin(admin.ModelAdmin):
    list_display = ('session', 'turn', 'score_global', 'created_at')
    search_fields = ('session__title',)

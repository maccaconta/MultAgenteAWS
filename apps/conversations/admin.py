from django.contrib import admin

from apps.conversations.models import AgentRun, ConversationSession, ConversationTurn


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "status", "blueprint", "created_at")
    list_filter = ("status", "blueprint", "persona", "scenario", "specialty")
    search_fields = ("title", "user__username", "user__email")
    autocomplete_fields = (
        "user",
        "blueprint",
        "persona",
        "scenario",
        "specialty",
        "policy",
        "instruction",
        "output_contract",
        "evaluation_rubric",
    )


@admin.register(ConversationTurn)
class ConversationTurnAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "sequence", "role", "speaker_name", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("content", "speaker_name", "session__title")
    autocomplete_fields = ("session",)


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ("id", "turn", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("content", "role", "turn__session__title")
    autocomplete_fields = ("turn",)

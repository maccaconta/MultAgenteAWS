from django.contrib import admin

from apps.catalog.models import (
    EvaluationRubricDefinition,
    InstructionDefinition,
    OutputContractDefinition,
    PersonaDefinition,
    PolicyDefinition,
    ScenarioDefinition,
    SimulationBlueprint,
    SpecialtyDefinition,
)


@admin.register(PersonaDefinition)
class PersonaDefinitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'slug', 'description')


@admin.register(ScenarioDefinition)
class ScenarioDefinitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'slug', 'description')


@admin.register(SpecialtyDefinition)
class SpecialtyDefinitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'slug', 'description')


@admin.register(PolicyDefinition)
class PolicyDefinitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'slug', 'description')


@admin.register(InstructionDefinition)
class InstructionDefinitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'slug', 'description')


@admin.register(OutputContractDefinition)
class OutputContractDefinitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'slug', 'description')


@admin.register(EvaluationRubricDefinition)
class EvaluationRubricDefinitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'slug', 'description')


@admin.register(SimulationBlueprint)
class SimulationBlueprintAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'persona', 'scenario', 'specialty', 'is_active')
    list_filter = ('is_active', 'persona', 'scenario', 'specialty')
    search_fields = ('title', 'slug', 'description')

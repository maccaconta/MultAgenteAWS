from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('catalog', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConversationSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('draft', 'Rascunho'), ('active', 'Ativa'), ('ended', 'Encerrada'), ('archived', 'Arquivada')], default='draft', max_length=16)),
                ('title', models.CharField(max_length=255)),
                ('session_state', models.JSONField(blank=True, default=dict)),
                ('latest_metrics', models.JSONField(blank=True, default=dict)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('blueprint', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sessions', to='catalog.simulationblueprint')),
                ('evaluation_rubric', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='sessions_as_rubric', to='catalog.promptcomponent')),
                ('instruction', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sessions_as_instruction', to='catalog.promptcomponent')),
                ('output_contract', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sessions_as_output', to='catalog.promptcomponent')),
                ('persona', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sessions_as_persona', to='catalog.promptcomponent')),
                ('policy', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sessions_as_policy', to='catalog.promptcomponent')),
                ('scenario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sessions_as_scenario', to='catalog.promptcomponent')),
                ('specialty', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sessions_as_specialty', to='catalog.promptcomponent')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='simulation_sessions', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ConversationTurn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequence', models.PositiveIntegerField()),
                ('role', models.CharField(choices=[('user', 'Usuário'), ('doctor_simulator', 'Médico simulado'), ('system', 'Sistema'), ('coach', 'Coach'), ('evaluator', 'Avaliador')], max_length=32)),
                ('speaker_name', models.CharField(blank=True, max_length=255)),
                ('content', models.TextField()),
                ('input_payload', models.JSONField(blank=True, default=dict)),
                ('output_payload', models.JSONField(blank=True, default=dict)),
                ('evidence_payload', models.JSONField(blank=True, default=dict)),
                ('telemetry', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='turns', to='conversations.conversationsession')),
            ],
            options={'ordering': ['sequence', 'created_at'], 'unique_together': {('session', 'sequence')}},
        ),
        migrations.CreateModel(
            name='ConversationArtifact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('artifact_type', models.CharField(max_length=64)),
                ('title', models.CharField(max_length=255)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='artifacts', to='conversations.conversationsession')),
                ('turn', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='artifacts', to='conversations.conversationturn')),
            ],
        ),
        migrations.CreateModel(
            name='AgentRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=32)),
                ('status', models.CharField(default='completed', max_length=32)),
                ('input_payload', models.JSONField(blank=True, default=dict)),
                ('output_payload', models.JSONField(blank=True, default=dict)),
                ('latency_ms', models.PositiveIntegerField(default=0)),
                ('tokens_in', models.PositiveIntegerField(default=0)),
                ('tokens_out', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('turn', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agent_runs', to='conversations.conversationturn')),
            ],
        ),
    ]

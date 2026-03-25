from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='PromptComponent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.SlugField(max_length=120, unique=True)),
                ('title', models.CharField(max_length=255)),
                ('component_type', models.CharField(choices=[('persona', 'Persona'), ('scenario', 'Cenário'), ('specialty', 'Especialidade'), ('policy', 'Política'), ('output_contract', 'Contrato de saída'), ('instruction', 'Instrução do agente'), ('rubric', 'Rubrica de avaliação')], max_length=40)),
                ('version', models.CharField(default='v1', max_length=32)),
                ('description', models.TextField(blank=True)),
                ('payload', models.JSONField(default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={'ordering': ['component_type', 'title'], 'unique_together': {('slug', 'version')}},
        ),
        migrations.CreateModel(
            name='SimulationBlueprint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.SlugField(max_length=120, unique=True)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('evaluation_rubric', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='blueprints_as_rubric', to='catalog.promptcomponent')),
                ('instruction', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='blueprints_as_instruction', to='catalog.promptcomponent')),
                ('output_contract', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='blueprints_as_output', to='catalog.promptcomponent')),
                ('persona', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='blueprints_as_persona', to='catalog.promptcomponent')),
                ('policy', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='blueprints_as_policy', to='catalog.promptcomponent')),
                ('scenario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='blueprints_as_scenario', to='catalog.promptcomponent')),
                ('specialty', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='blueprints_as_specialty', to='catalog.promptcomponent')),
            ],
        ),
    ]

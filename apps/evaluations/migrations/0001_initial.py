from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('conversations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EvaluationSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('turn', models.PositiveIntegerField(default=0)),
                ('score_global', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('dimensions', models.JSONField(blank=True, default=dict)),
                ('strengths', models.JSONField(blank=True, default=list)),
                ('improvements', models.JSONField(blank=True, default=list)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evaluation_snapshots', to='conversations.conversationsession')),
            ],
        ),
    ]

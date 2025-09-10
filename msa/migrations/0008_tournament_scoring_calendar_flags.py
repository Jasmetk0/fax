from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("msa", "0007_planningundostate"),
    ]

    operations = [
        migrations.AddField(
            model_name="tournament",
            name="calendar_sync_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="tournament",
            name="is_finals",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="tournament",
            name="scoring_md",
            field=models.JSONField(blank=True, null=True, default=dict),
        ),
        migrations.AddField(
            model_name="tournament",
            name="scoring_qual_win",
            field=models.JSONField(blank=True, null=True, default=dict),
        ),
    ]

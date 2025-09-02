from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("msa", "0018_tournamententry_soft_delete"),
    ]

    operations = [
        migrations.AddField(
            model_name="match",
            name="position",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="match",
            constraint=models.UniqueConstraint(
                fields=("tournament", "round", "position"),
                condition=Q(position__isnull=False),
                name="match_unique_round_position",
            ),
        ),
    ]

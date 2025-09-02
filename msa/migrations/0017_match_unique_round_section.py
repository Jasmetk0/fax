from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("msa", "0016_tournament_world_ranking_mode_and_more"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="match",
            constraint=models.UniqueConstraint(
                fields=["tournament", "round", "section"],
                name="match_unique_round_section",
                condition=Q(section__gt="") & ~Q(section__contains='"'),
            ),
        ),
    ]

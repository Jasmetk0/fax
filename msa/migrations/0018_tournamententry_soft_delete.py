from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("msa", "0017_match_unique_round_section"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="tournamententry",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="tournamententry",
            constraint=models.UniqueConstraint(
                fields=["tournament", "player"],
                condition=Q(status="active"),
                name="unique_active_entry",
            ),
        ),
    ]

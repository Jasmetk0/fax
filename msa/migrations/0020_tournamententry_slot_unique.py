from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("msa", "0019_match_position"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="tournamententry",
            constraint=models.UniqueConstraint(
                fields=["tournament", "position"],
                condition=Q(status="active")
                & Q(position__isnull=False)
                & ~Q(entry_type="ALT"),
                name="unique_active_slot",
            ),
        ),
    ]

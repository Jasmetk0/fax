import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("msa", "0008_tournament_scoring_calendar_flags"),
    ]

    operations = [
        migrations.CreateModel(
            name="Country",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("iso3", models.CharField(max_length=3, unique=True)),
                ("iso2", models.CharField(max_length=2, null=True, blank=True)),
                ("name", models.CharField(max_length=80, null=True, blank=True)),
            ],
            options={"ordering": ["iso3"]},
        ),
        migrations.AddField(
            model_name="player",
            name="full_name",
            field=models.CharField(max_length=160, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="player",
            name="first_name",
            field=models.CharField(max_length=80, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="player",
            name="last_name",
            field=models.CharField(max_length=80, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="player",
            name="birthdate",
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="player",
            name="country",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.SET_NULL,
                to="msa.country",
                null=True,
                blank=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="player",
            constraint=models.CheckConstraint(
                name="player_name_parts_or_full",
                check=(
                    models.Q(full_name__isnull=False) & ~models.Q(full_name="")
                    | (
                        models.Q(first_name__isnull=False)
                        & ~models.Q(first_name="")
                        & models.Q(last_name__isnull=False)
                        & ~models.Q(last_name="")
                    )
                ),
            ),
        ),
    ]

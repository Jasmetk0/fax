import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("msa", "0011_categoryseason_tournament"),
    ]

    operations = [
        migrations.CreateModel(
            name="RoundFormat",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "tournament",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="msa.tournament"
                    ),
                ),
                (
                    "phase",
                    models.CharField(
                        choices=[("QUAL", "Qualification"), ("MD", "Main Draw")], max_length=8
                    ),
                ),
                ("round_name", models.CharField(max_length=16)),
                ("best_of", models.PositiveSmallIntegerField(choices=[(3, "3"), (5, "5")])),
                ("win_by_two", models.BooleanField(default=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="roundformat",
            constraint=models.UniqueConstraint(
                fields=["tournament", "phase", "round_name"], name="uniq_round_format"
            ),
        ),
    ]

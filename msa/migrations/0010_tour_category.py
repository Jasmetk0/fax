import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("msa", "0009_country_player"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tour",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=64, unique=True)),
                ("rank", models.PositiveSmallIntegerField(default=100)),
                ("code", models.CharField(max_length=16, null=True, blank=True, unique=True)),
            ],
            options={"ordering": ["rank", "name"]},
        ),
        migrations.AddField(
            model_name="category",
            name="tour",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to="msa.tour", null=True, blank=True
            ),
        ),
        migrations.AddField(
            model_name="category",
            name="rank",
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="category",
            name="kind",
            field=models.CharField(
                max_length=32,
                choices=[
                    ("STANDARD", "Standard"),
                    ("FINALS", "Finals"),
                    ("TEAM", "Team"),
                    ("EXHIBITION", "Exhibition"),
                    ("WC_QUALIFICATION", "WC Qualification"),
                ],
                default="STANDARD",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterModelOptions(
            name="category",
            options={"ordering": ["tour__rank", "rank", "name"]},
        ),
        migrations.AddField(
            model_name="tournament",
            name="kind",
            field=models.CharField(
                max_length=32,
                choices=[
                    ("STANDARD", "Standard"),
                    ("FINALS", "Finals"),
                    ("TEAM", "Team"),
                    ("EXHIBITION", "Exhibition"),
                    ("WC_QUALIFICATION", "WC Qualification"),
                ],
                null=True,
                blank=True,
            ),
        ),
    ]

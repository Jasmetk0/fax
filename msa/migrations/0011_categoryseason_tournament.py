import django.core.validators
from django.db import migrations, models

import msa.models


class Migration(migrations.Migration):
    dependencies = [
        ("msa", "0010_tour_category"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="categoryseason",
            name="qualifiers_count",
        ),
        migrations.AddField(
            model_name="categoryseason",
            name="name",
            field=models.CharField(max_length=120, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="categoryseason",
            name="draw_size",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (16, "16"),
                    (24, "24"),
                    (28, "28"),
                    (32, "32"),
                    (48, "48"),
                    (56, "56"),
                    (60, "60"),
                    (64, "64"),
                    (96, "96"),
                    (112, "112"),
                    (120, "120"),
                    (124, "124"),
                    (128, "128"),
                ],
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="categoryseason",
            name="md_seeds_count",
            field=models.PositiveSmallIntegerField(
                default=8,
                null=True,
                blank=True,
                validators=[msa.models.validate_power_of_two],
            ),
        ),
        migrations.AlterField(
            model_name="season",
            name="name",
            field=models.CharField(
                max_length=32,
                unique=True,
                null=True,
                blank=True,
                validators=[
                    django.core.validators.RegexValidator(
                        r"^\d{4}/\d{2}$", message="Season name must be YYYY/NN"
                    ),
                ],
            ),
        ),
        migrations.AddField(
            model_name="tournament",
            name="qualifiers_count",
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="tournament",
            name="md_best_of",
            field=models.PositiveSmallIntegerField(
                choices=[(3, "3"), (5, "5")], default=5, null=True, blank=True
            ),
        ),
        migrations.AlterField(
            model_name="tournament",
            name="q_best_of",
            field=models.PositiveSmallIntegerField(
                choices=[(3, "3"), (5, "5")], default=3, null=True, blank=True
            ),
        ),
    ]

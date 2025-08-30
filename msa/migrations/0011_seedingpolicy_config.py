from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("msa", "0010_pointsrow_prizerow"),
    ]

    operations = [
        migrations.AddField(
            model_name="seedingpolicy",
            name="config",
            field=models.JSONField(default=dict),
        ),
    ]

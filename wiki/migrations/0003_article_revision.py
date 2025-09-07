import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wiki", "0002_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="summary",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="article",
            name="status",
            field=models.CharField(
                choices=[("draft", "Draft"), ("published", "Published")],
                default="published",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="article",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="ArticleRevision",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("summary", models.TextField(blank=True)),
                ("content_md", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "article",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="revisions",
                        to="wiki.article",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]

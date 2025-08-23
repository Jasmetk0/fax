from django.db import migrations
from django.db.models import Q
from django.utils.text import slugify


def generate_slugs(apps, schema_editor):
    Player = apps.get_model("msa", "Player")
    qs = Player.objects.filter(Q(slug__isnull=True) | Q(slug=""))
    for player in qs.iterator():
        base_slug = slugify(player.name)
        slug = base_slug
        counter = 2
        while Player.objects.filter(slug=slug).exclude(pk=player.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        player.slug = slug
        player.save(update_fields=["slug"])


class Migration(migrations.Migration):
    dependencies = [
        ("msa", "0002_player_current_points_player_current_rank_and_more"),
    ]

    operations = [migrations.RunPython(generate_slugs, migrations.RunPython.noop)]

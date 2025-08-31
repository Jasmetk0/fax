from django.db import migrations


def create_entries(apps, schema_editor):
    Tournament = apps.get_model("msa", "Tournament")
    Match = apps.get_model("msa", "Match")
    Player = apps.get_model("msa", "Player")
    TournamentEntry = apps.get_model("msa", "TournamentEntry")
    for tournament in Tournament.objects.all():
        player_ids = set()
        for p1_id, p2_id in Match.objects.filter(tournament=tournament).values_list(
            "player1_id", "player2_id"
        ):
            if p1_id:
                player_ids.add(p1_id)
            if p2_id:
                player_ids.add(p2_id)
        created = 0
        for pid in player_ids:
            player = Player.objects.get(pk=pid)
            _, was_created = TournamentEntry.objects.get_or_create(
                tournament=tournament,
                player=player,
                defaults={"entry_type": "DA", "status": "active"},
            )
            if was_created:
                created += 1
        if created:
            print(f"Tournament {tournament.id}: created {created} entries")


def reverse(apps, schema_editor):
    # No-op reverse migration
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("msa", "0014_tournament_allow_manual_bracket_edits_and_more"),
    ]

    operations = [migrations.RunPython(create_entries, reverse)]

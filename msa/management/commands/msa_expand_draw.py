from django.core.management.base import BaseCommand

from ...models import EventPhase, EventMatch, PhaseRound
from ...services.draw_engine import expand_template


class Command(BaseCommand):
    help = "Expand event draw from template"

    def add_arguments(self, parser):
        parser.add_argument("event_id", type=int)

    def handle(self, *args, **options):
        event_id = options["event_id"]
        expand_template(event_id)
        phases = EventPhase.objects.filter(event_id=event_id).count()
        rounds = PhaseRound.objects.filter(phase__event_id=event_id).count()
        matches = EventMatch.objects.filter(phase__event_id=event_id).count()
        self.stdout.write(f"{phases} phases, {rounds} rounds, {matches} matches")

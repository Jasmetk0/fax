import pytest
from django.db import IntegrityError
from django.test import TestCase

from msa.models import Match, Tournament


class MatchConstraintTests(TestCase):
    def test_unique_match_tournament_round_position(self):
        t = Tournament.objects.create(name="T", slug="t", draw_size=32)
        Match.objects.create(tournament=t, round="R16", position=1)
        with pytest.raises(IntegrityError):
            Match.objects.create(tournament=t, round="R16", position=1)

from django.test import TestCase

from msa.models import Match, Tournament
from msa.services.qual import generate_qualifying


class QualBestOfPolicyTests(TestCase):
    def test_qual_uses_q_best_of(self):
        t = Tournament.objects.create(
            name="TQ",
            slug="tq",
            draw_size=32,
            q_best_of=3,
            md_best_of=5,
        )
        # Funkce musí vytvořit aspoň 1 kvalifikační zápas
        generate_qualifying(t)

        qs = Match.objects.filter(tournament=t)
        self.assertTrue(
            qs.exists(),
            "Qual generator must create at least one qualifying match",
        )
        for m in qs:
            self.assertEqual(m.best_of, 3)

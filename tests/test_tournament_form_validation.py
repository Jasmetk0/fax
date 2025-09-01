from django.test import TestCase

from msa.forms import TournamentForm


class TournamentFormValidationTests(TestCase):
    def test_seeds_exceed_draw(self):
        form = TournamentForm(
            data={"name": "T", "slug": "t", "draw_size": 16, "seeds_count": 17}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Seeds exceed draw size", form.errors["__all__"])

    def test_seeds_plus_qualifiers_exceed_draw(self):
        form = TournamentForm(
            data={
                "name": "T2",
                "slug": "t2",
                "draw_size": 16,
                "seeds_count": 8,
                "qualifiers_count": 9,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Seeds+qualifiers exceed draw size", form.errors["__all__"])

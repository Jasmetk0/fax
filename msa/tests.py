from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import (
    Season,
    Category,
    CategorySeason,
    EventBrand,
    EventEdition,
    DrawTemplate,
    EventPhase,
    PhaseRound,
)
from .templatetags.msa_extras import get_draw_label


class AdminModeTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.staff = User.objects.create_user("staff", password="x", is_staff=True)

    def _toggle_admin(self, on=True):
        self.client.force_login(self.staff)
        self.client.get(reverse("msa:admin-mode-toggle"), {"on": "1" if on else "0"})

    def test_admin_buttons_visibility(self):
        self._toggle_admin(True)
        resp = self.client.get(reverse("msa:tournament-list"))
        self.assertContains(resp, "Add Season")
        self._toggle_admin(False)
        resp = self.client.get(reverse("msa:tournament-list"))
        self.assertNotContains(resp, "Add Season")

    def test_crud_flow(self):
        self._toggle_admin(True)
        # Create season
        self.client.post(reverse("msa:season-create"), {"name": "2024", "code": "2024"})
        season = Season.objects.get()
        # Create category
        self.client.post(reverse("msa:category-create"), {"name": "World"})
        category = Category.objects.get()
        # Create seasoncategory
        self.client.post(
            reverse("msa:seasoncategory-create"),
            {"season": season.pk, "category": category.pk, "label": "WT"},
        )
        sc = CategorySeason.objects.get()
        # Prepare brand and template
        brand = EventBrand.objects.create(name="Brand")
        tmpl = DrawTemplate.objects.create(
            code="se64",
            name="SE64",
            dsl_json={
                "phases": [
                    {
                        "type": "single_elim",
                        "config": {"draw": "single_elim", "size": 64},
                    }
                ]
            },
        )
        data = {
            "name": "Open",
            "brand": brand.pk,
            "season": season.pk,
            "category_season": sc.pk,
            "start_date": timezone.now().date(),
            "end_date": timezone.now().date(),
            "venue": "V",
            "city": "C",
            "best_of": 5,
            "sanction_status": "ok",
            "points_eligible": True,
            "draw_template": tmpl.pk,
        }
        self.client.post(reverse("msa:event-create"), data)
        event = EventEdition.objects.get()
        resp = self.client.get(reverse("msa:tournament-list"), {"season": season.pk})
        self.assertContains(resp, "Open")
        # Edit
        data["name"] = "Open2"
        self.client.post(reverse("msa:event-edit", args=[event.pk]), data)
        event.refresh_from_db()
        self.assertEqual(event.name, "Open2")
        # Delete
        self.client.post(reverse("msa:event-delete", args=[event.pk]))
        self.assertEqual(EventEdition.objects.count(), 0)

    def test_get_draw_label(self):
        season = Season.objects.create(name="2024")
        brand = EventBrand.objects.create(name="Brand")
        event = EventEdition.objects.create(name="E", brand=brand, season=season)
        phase = EventPhase.objects.create(
            event=event, order=1, type="single_elim", name="Main"
        )
        PhaseRound.objects.create(
            phase=phase,
            order=1,
            code="R64",
            label="R64",
            entrants=64,
            matches=32,
            best_of=5,
        )
        self.assertEqual(get_draw_label(event), "Single Elim 64")
        EventPhase.objects.create(event=event, order=0, type="qualifying", name="Q")
        self.assertEqual(get_draw_label(event), "Single Elim 64 + Qualifying")

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from msa.models import Player, Tournament, TournamentEntry
from msa.services.entries import validate_pre_draw, set_seed


class LockSeedsExportTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 10)]
        User = get_user_model()
        self.staff = User.objects.create_user("admin", password="x", is_staff=True)
        self.client.force_login(self.staff)
        session = self.client.session
        session["admin_mode"] = True
        session.save()

    def _url(self, t):
        return reverse("msa:tournament-players", args=[t.slug])

    def test_lock_and_unlock_state_transitions(self):
        t = Tournament.objects.create(name="T", slug="t", state=Tournament.State.DRAFT)
        url = self._url(t)
        self.client.post(url, {"action": "entries_lock"}, follow=True)
        t.refresh_from_db()
        self.assertEqual(t.state, Tournament.State.ENTRY_LOCKED)
        self.client.post(url, {"action": "entries_unlock"}, follow=True)
        t.refresh_from_db()
        self.assertEqual(t.state, Tournament.State.ENTRY_OPEN)
        t2 = Tournament.objects.create(
            name="T2", slug="t2", state=Tournament.State.DRAWN
        )
        url2 = self._url(t2)
        res = self.client.post(url2, {"action": "entries_unlock"}, follow=True)
        t2.refresh_from_db()
        self.assertEqual(t2.state, Tournament.State.DRAWN)
        messages = [m.message for m in get_messages(res.wsgi_request)]
        self.assertTrue(any("Cannot" in m for m in messages))

    def test_checklist_capacity_and_seeds(self):
        t = Tournament.objects.create(name="T", slug="tt", draw_size=2, seeds_count=2)
        e1 = TournamentEntry.objects.create(
            tournament=t, player=self.players[0], seed=1
        )
        result = validate_pre_draw(t)
        self.assertTrue(result["warnings"])  # under capacity
        TournamentEntry.objects.create(tournament=t, player=self.players[1])
        e3 = TournamentEntry.objects.create(tournament=t, player=self.players[2])
        result = validate_pre_draw(t)
        self.assertTrue(result["errors"])  # over capacity
        e1.seed = 1
        e1.save(update_fields=["seed"])
        e3.seed = 3
        e3.save(update_fields=["seed"])
        e3.status = TournamentEntry.Status.WITHDRAWN
        e3.save(update_fields=["status"])
        e2 = TournamentEntry.objects.get(tournament=t, player=self.players[1])
        e2.seed = 1
        e2.save(update_fields=["seed"])
        result = validate_pre_draw(t)
        self.assertTrue(any("Duplicate" in e for e in result["errors"]))
        self.assertTrue(any("out of range" in e for e in result["errors"]))
        self.assertTrue(any("not active" in e for e in result["errors"]))

    def test_seed_update_rules(self):
        t = Tournament.objects.create(
            name="T1", slug="s1", seeding_method="manual", seeds_count=2
        )
        e1 = TournamentEntry.objects.create(tournament=t, player=self.players[0])
        e2 = TournamentEntry.objects.create(tournament=t, player=self.players[1])
        ok, _ = set_seed(e1, 1, self.staff)
        self.assertTrue(ok)
        ok, msg = set_seed(e2, 1, self.staff)
        self.assertFalse(ok)
        t2 = Tournament.objects.create(
            name="T2", slug="s2", seeding_method="ranking_snapshot"
        )
        e3 = TournamentEntry.objects.create(tournament=t2, player=self.players[2])
        ok, _ = set_seed(e3, 1, self.staff)
        self.assertFalse(ok)
        t3 = Tournament.objects.create(
            name="T3",
            slug="s3",
            seeding_method="ranking_snapshot",
            flex_mode=True,
            seeds_count=2,
        )
        e4 = TournamentEntry.objects.create(tournament=t3, player=self.players[3])
        ok, msg = set_seed(e4, 1, self.staff)
        self.assertTrue(ok)
        self.assertIn("warning", msg)

    def test_bulk_set_seeds_mapping(self):
        t = Tournament.objects.create(
            name="T4", slug="s4", seeding_method="manual", seeds_count=3
        )
        e1 = TournamentEntry.objects.create(tournament=t, player=self.players[0])
        e2 = TournamentEntry.objects.create(tournament=t, player=self.players[1])
        text = f"{e1.id},2\n\n#c\n999,1\n{e2.id},2\n"
        url = self._url(t)
        res = self.client.post(
            url,
            {"action": "seeds_bulk_update", "rows": text},
            follow=True,
        )
        e1.refresh_from_db()
        e2.refresh_from_db()
        self.assertEqual(e1.seed, 2)
        self.assertIsNone(e2.seed)
        messages = [m.message for m in get_messages(res.wsgi_request)]
        self.assertTrue(any("updated 1" in m for m in messages))
        self.assertTrue(any("999" in m for m in messages))

    def test_entries_export_csv_format(self):
        t = Tournament.objects.create(name="T5", slug="s5")
        TournamentEntry.objects.create(tournament=t, player=self.players[0])
        TournamentEntry.objects.create(tournament=t, player=self.players[1], seed=1)
        url = self._url(t)
        res = self.client.get(url, {"action": "entries_export_csv"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "text/csv")
        lines = res.content.decode().splitlines()
        self.assertEqual(
            lines[0],
            "player_id,player_name,entry_type,status,seed,position,origin_note",
        )
        self.assertEqual(
            len(lines) - 1, TournamentEntry.objects.filter(tournament=t).count()
        )

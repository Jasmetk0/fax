import json
import time
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from msa.models import Player, Tournament, TournamentEntry
from msa.services.draw import generate_draw
from msa.services.share import make_share_token


class ShareAndPermalinkTests(TestCase):
    def setUp(self):
        self.players = [Player.objects.create(name=f"P{i}") for i in range(1, 80)]
        User = get_user_model()
        self.staff = User.objects.create_user("admin", password="x", is_staff=True)
        self.client.force_login(self.staff)
        session = self.client.session
        session["admin_mode"] = True
        session.save()

    def _create_entries(self, tournament, total, entry_type=None):
        for i in range(total):
            kwargs = {"tournament": tournament, "player": self.players[i]}
            if entry_type:
                kwargs["entry_type"] = entry_type
            TournamentEntry.objects.create(**kwargs)

    def test_share_html_main_ok_and_no_admin_controls(self):
        t = Tournament.objects.create(name="T", slug="t", draw_size=32)
        self._create_entries(t, 32)
        generate_draw(t)
        url = reverse("msa:tournament-draw", args=[t.slug])
        self.client.post(
            url,
            {"action": "share_link", "variant": "main", "format": "html"},
        )
        token = self.client.session["share_url"].split("share=")[1]
        resp = self.client.get(f"{url}?share={token}")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["is_admin"])
        self.assertContains(resp, self.players[0].name)
        self.assertNotContains(resp, 'name="action"')

    def test_share_json_qual_ok_with_rounds_filter(self):
        t = Tournament.objects.create(name="TQ", slug="tq", draw_size=32)
        for i in range(4):
            TournamentEntry.objects.create(
                tournament=t, player=self.players[i], entry_type="Q"
            )
        from msa.models import Match

        Match.objects.create(
            tournament=t,
            player1=self.players[0],
            player2=self.players[1],
            round="Q2",
        )
        Match.objects.create(
            tournament=t,
            player1=self.players[2],
            player2=self.players[3],
            round="QF",
        )
        token = make_share_token(t.slug, "qual", "json", ["Q2", "QF"])
        url = reverse("msa:tournament-qualifying-json", args=[t.slug])
        resp = self.client.get(f"{url}?share={token}")
        data = json.loads(resp.content)
        codes = [r["code"] for r in data["rounds"]]
        self.assertEqual(codes, ["Q2", "QF"])

    def test_share_token_expired(self):
        t = Tournament.objects.create(name="TE", slug="te", draw_size=32)
        self._create_entries(t, 32)
        generate_draw(t)
        self.client.logout()
        with override_settings(MSA_SHARE_TTL_DAYS=0):
            token = make_share_token(t.slug, "main", "html")
            time.sleep(1)
            url = reverse("msa:tournament-draw", args=[t.slug])
            resp = self.client.get(f"{url}?share={token}")
            self.assertEqual(resp.status_code, 403)

    def test_rounds_query_without_share(self):
        t = Tournament.objects.create(name="TR", slug="tr", draw_size=32)
        self._create_entries(t, 32)
        generate_draw(t)
        url = reverse("msa:tournament-draw-json", args=[t.slug])
        resp = self.client.get(f"{url}?rounds=R32")
        data = json.loads(resp.content)
        self.assertEqual([r["code"] for r in data["rounds"]], ["R32"])

    def test_public_blocks_post(self):
        t = Tournament.objects.create(name="TB", slug="tb", draw_size=32)
        self._create_entries(t, 32)
        generate_draw(t)
        self.client.logout()
        token = make_share_token(t.slug, "main", "html")
        url = reverse("msa:tournament-draw", args=[t.slug])
        resp = self.client.post(f"{url}?share={token}", {"action": "anything"})
        self.assertEqual(resp.status_code, 403)

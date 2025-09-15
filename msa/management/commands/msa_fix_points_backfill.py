from __future__ import annotations

from django.core.management.base import BaseCommand

from msa.models import Tournament
from msa.utils.rounds import round_labels_from_md_size


def _get_md_size_and_flags(t: Tournament) -> tuple[int | None, bool]:
    cs = getattr(t, "category_season", None)
    md = (
        getattr(cs, "draw_size", None)
        or getattr(t, "main_draw_size", None)
        or getattr(t, "draw_size", None)
    )
    tp = None
    for name in ("third_place_enabled", "third_place", "has_third_place", "bronze_match"):
        if tp is None and cs is not None:
            tp = getattr(cs, name, None)
        if tp is None:
            tp = getattr(t, name, None)
    return (int(md) if md else None, bool(tp))


class Command(BaseCommand):
    help = "Backfill scoring maps: ensure 'W', initial R{md_size}, third-place keys, and 'Q-W' for qualifiers."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", default=False)

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        updated = 0

        def _alias_lookup(cur: dict[str, int], key: str) -> int | None:
            if key in cur:
                return cur[key]
            if key == "W" and "Winner" in cur:
                return cur["Winner"]
            if key == "F" and "RunnerUp" in cur:
                return cur["RunnerUp"]
            if key in ("3rd", "4th") and "SF" in cur:
                return cur["SF"]
            return None

        for t in Tournament.objects.all():
            md_size, tp = _get_md_size_and_flags(t)
            if not md_size:
                continue
            desired = round_labels_from_md_size(md_size, third_place=tp)
            current_md = dict(t.scoring_md or {})
            new_md = {}
            for k in desired:
                v = _alias_lookup(current_md, k)
                new_md[k] = int(v) if v is not None else 0

            current_q = dict(t.scoring_qual_win or {})
            qual_rounds = sum(1 for k in current_q if k.startswith("Q-R"))
            new_q = {f"Q-R{i}": current_q.get(f"Q-R{i}", 0) for i in range(1, qual_rounds + 1)}
            if qual_rounds > 0:
                new_q["Q-W"] = current_q.get("Q-W", 0)

            if new_md != current_md or new_q != current_q:
                if not dry:
                    t.scoring_md = new_md
                    t.scoring_qual_win = new_q
                    t.save(update_fields=["scoring_md", "scoring_qual_win"])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Updated: {updated} (dry={dry})"))

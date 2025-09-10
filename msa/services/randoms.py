import hashlib
import random
from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any


def rng_for(tournament) -> random.Random:
    seed = int(getattr(tournament, "rng_seed_active", 0) or 0)
    if not seed:
        base = f"{getattr(tournament, 'slug', '')}:{getattr(tournament, 'start_date', '')}"
        digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
        seed = int(digest[:8], 16) % (2**31)
    return random.Random(seed)


def seeded_shuffle(seq: Sequence[Any], rng: random.Random):
    return rng.sample(list(seq), k=len(seq))


def rng_from_seed_or_tournament_and_persist(tournament, rng_seed: int | None):
    """
    Vrátí (rng, used_seed). Pokud je rng_seed předán, použije se a uloží do
    tournament.rng_seed_active (pokud se liší). Jinak použije rng_for(tournament).
    """

    if rng_seed is not None:
        rng = rng_for(SimpleNamespace(rng_seed_active=int(rng_seed)))
        if getattr(tournament, "rng_seed_active", None) != int(rng_seed):
            tournament.rng_seed_active = int(rng_seed)
            tournament.save(update_fields=["rng_seed_active"])
        return rng, int(rng_seed)
    return rng_for(tournament), int(getattr(tournament, "rng_seed_active", 0) or 0)

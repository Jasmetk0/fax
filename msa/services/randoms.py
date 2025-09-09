import random
from collections.abc import Sequence
from typing import Any


def rng_for(tournament) -> random.Random:
    seed = int(getattr(tournament, "rng_seed_active", 0) or 0)
    if not seed:
        base = f"{getattr(tournament, 'slug', '')}:{getattr(tournament, 'start_date', '')}"
        seed = abs(hash(base)) % (2**31)
    return random.Random(seed)


def seeded_shuffle(seq: Sequence[Any], rng: random.Random):
    return rng.sample(list(seq), k=len(seq))

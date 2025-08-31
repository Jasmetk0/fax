from django.conf import settings


def _generate_draw_legacy(tournament, force: bool = False):
    """Placeholder for legacy draw generation."""
    return None


def _generate_draw_v1(tournament, force: bool = False):
    """Placeholder for v1 draw generation."""
    return None


def generate_draw(tournament, force: bool = False):
    """Generate tournament draw using configured engine."""
    engine = getattr(settings, "MSA_DRAW_ENGINE", "v1")
    if engine == "legacy":
        return _generate_draw_legacy(tournament, force=force)
    if engine == "v1":
        return _generate_draw_v1(tournament, force=force)
    raise ValueError(f"Unknown draw engine: {engine}")

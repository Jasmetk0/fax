from django import template

from ..services.rounds import round_label as _round_label


def _round_size_from_template(event):
    tmpl = getattr(event.draw_template, "dsl_json", {}) or {}
    phases = tmpl.get("phases", [])
    if phases:
        config = phases[0].get("config", {})
        size = config.get("size") or config.get("entrants")
        draw = config.get("draw")
        if draw == "single_elim" and size:
            return f"Single Elim {size}", any(
                p.get("type") == "qualifying" for p in phases
            )
    return "", any(p.get("type") == "qualifying" for p in phases)


register = template.Library()


@register.simple_tag
def get_draw_label(event):
    if event.phases.exists():
        se_phase = (
            event.phases.filter(type="single_elim").prefetch_related("rounds").first()
        )
        label = ""
        if se_phase:
            round1 = se_phase.rounds.order_by("order").first()
            if round1:
                label = f"Single Elim {round1.entrants}"
        if event.phases.filter(type="qualifying").exists():
            if label:
                label += " + Qualifying"
            else:
                label = "Qualifying"
        return label
    label, has_q = _round_size_from_template(event)
    if has_q and label:
        label += " + Qualifying"
    return label


@register.filter
def round_label(code: str) -> str:
    if code.startswith("R") and code[1:].isdigit():
        return _round_label(int(code[1:]))
    mapping = {"QF": 8, "SF": 4, "F": 2}
    size = mapping.get(code)
    if size:
        return _round_label(size)
    if code == "3P":
        return "3rd place"
    return code

"""Context processors for Woorld calendar."""


def woorld_date(request):
    """Add current Woorld date stored in session to templates."""
    return {"WOORLD_CURRENT_DATE": request.session.get("woorld_current_date", "")}

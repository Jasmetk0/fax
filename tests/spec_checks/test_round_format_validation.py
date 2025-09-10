import pytest
from django.core.exceptions import ValidationError

from msa.models import Phase, RoundFormat
from msa.services.round_format import get_round_format
from tests.factories import make_tournament


@pytest.mark.django_db
def test_round_format_validation_and_fallback():
    t = make_tournament()
    rf = RoundFormat(tournament=t, phase=Phase.MD, round_name="QF", best_of=4)
    with pytest.raises(ValidationError):
        rf.full_clean()
    assert get_round_format(t, Phase.QUAL, "QF") == (3, True)
    assert get_round_format(t, Phase.MD, "QF") == (5, True)

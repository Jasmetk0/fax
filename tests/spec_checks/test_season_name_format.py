import pytest
from django.core.exceptions import ValidationError

from msa.models import Season


def test_season_name_format(db):
    Season(name="2005/06").full_clean()
    with pytest.raises(ValidationError):
        Season(name="2005-06").full_clean()

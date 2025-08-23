import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_article_form_has_infobox_schemas(client, django_user_model):
    user = django_user_model.objects.create_user("admin", password="pw", is_staff=True)
    client.force_login(user)
    session = client.session
    session["admin_mode"] = True
    session.save()
    resp = client.get(reverse("wiki:article-create"))
    assert resp.status_code == 200
    schemas = resp.context["infobox_schemas"]
    assert "country" in schemas and "city" in schemas

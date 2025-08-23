from django.urls import reverse


def _header_html(response):
    return response.content.decode().split("<main", 1)[0]


def test_home_page(client):
    url = reverse("home")
    response = client.get(url)
    assert response.status_code == 200
    assert b"Wiki" in response.content
    assert b"MSA" in response.content


def test_topbar_no_msa_link(client):
    response = client.get(reverse("home"))
    header = _header_html(response)
    assert "/msasquashtour/" not in header


def test_topbar_admin_link_visibility(client, django_user_model):
    url = reverse("home")
    response = client.get(url)
    header = _header_html(response)
    assert "Admin" not in header
    assert "/admin/" not in header
    staff = django_user_model.objects.create_user("s", password="x", is_staff=True)
    client.force_login(staff)
    response = client.get(url)
    header = _header_html(response)
    assert "Admin" in header
    assert "/admin/" in header

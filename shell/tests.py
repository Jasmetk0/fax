from django.urls import reverse


def test_home_page(client):
    url = reverse("home")
    response = client.get(url)
    assert response.status_code == 200

def test_homepage_contains_wiki(client):
    response = client.get("/")
    assert b"Wiki" in response.content

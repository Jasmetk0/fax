from django.urls import reverse

from wiki.models import Article


def test_search_empty(client):
    response = client.get(reverse("search"))
    assert response.status_code == 200
    assert "Zadejte dotaz" in response.text


def test_search_article_found(client):
    Article.objects.create(title="Woorld Test", content_md="Hello")
    response = client.get(reverse("search"), {"q": "woorld"})
    assert response.status_code == 200
    assert "Woorld Test" in response.text


def test_fuzzy_search_and_suggest(client):
    Article.objects.create(title="Oliver", content_md="Exact")
    Article.objects.create(title="Olivier", content_md="Fuzzy")

    response = client.get(reverse("search"), {"q": "Oliver"})
    assert response.status_code == 200
    content = response.text
    assert "Oliver" in content
    assert "Olivier" in content
    assert content.index("Oliver") < content.index("Olivier")

    resp = client.get(reverse("search-suggest"), {"q": "Oliver"})
    assert resp.status_code == 200
    titles = [r["title"] for r in resp.json()["results"]]
    assert "Oliver" in titles
    assert "Olivier" in titles
    assert titles.index("Oliver") < titles.index("Olivier")

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

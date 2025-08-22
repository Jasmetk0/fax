import pytest
from django.urls import reverse
from .models import Article


@pytest.mark.django_db
def test_article_list(client):
    Article.objects.create(title="Test", content_md="text")
    url = reverse("wiki:article-list")
    resp = client.get(url)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_article_detail(client):
    article = Article.objects.create(title="Detail", content_md="text")
    url = reverse("wiki:article-detail", args=[article.slug])
    resp = client.get(url)
    assert resp.status_code == 200


def test_placeholder():
    assert True

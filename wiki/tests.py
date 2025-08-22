import pytest
from django.urls import reverse
from .models import Article


@pytest.mark.django_db
def test_article_list(client):
    Article.objects.create(title="Test", content_md="text")
    resp = client.get(reverse("wiki:article-list"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_article_detail(client):
    a = Article.objects.create(title="Detail", content_md="text")
    resp = client.get(reverse("wiki:article-detail", args=[a.slug]))
    assert resp.status_code == 200

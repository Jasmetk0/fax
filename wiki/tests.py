import pytest
from django.urls import reverse
from .models import Article, Category, CategoryArticle


@pytest.mark.django_db
def test_article_list(client):
    Article.objects.create(title="Test", content_md="text")
    url = reverse("wiki:article-list")
    resp = client.get(url)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_homepage_shows_categories(client):
    art = Article.objects.create(title="Home", content_md="text")
    cat = Category.objects.create(name="Cat", color="#ff0000", order=1)
    CategoryArticle.objects.create(category=cat, article=art, order=1)
    resp = client.get(reverse("wiki:article-list"))
    assert "Cat" in resp.text
    assert "Home" in resp.text


@pytest.mark.django_db
def test_article_detail(client):
    article = Article.objects.create(title="Detail", content_md="text")
    url = reverse("wiki:article-detail", args=[article.slug])
    resp = client.get(url)
    assert resp.status_code == 200

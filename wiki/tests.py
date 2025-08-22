import pytest
from django.urls import reverse
from django.utils.text import slugify
from .models import Article, Category, CategoryArticle, ArticleRevision


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


@pytest.mark.django_db
def test_article_create_redirects(client, django_user_model):
    user = django_user_model.objects.create_user("admin", password="pw", is_staff=True)
    client.force_login(user)
    session = client.session
    session["admin_mode"] = True
    session.save()
    url = reverse("wiki:article-create")
    resp = client.post(
        url,
        {"title": "Create", "summary": "", "content_md": "text", "status": "published"},
    )
    assert resp.status_code == 302
    detail_url = reverse("wiki:article-detail", args=["create"])
    assert resp.headers["Location"].endswith(detail_url)


@pytest.mark.django_db
def test_staff_edit_creates_revision(client, django_user_model):
    user = django_user_model.objects.create_user("admin", password="pw", is_staff=True)
    client.force_login(user)
    session = client.session
    session["admin_mode"] = True
    session.save()
    article = Article.objects.create(title="A", content_md="one")
    url = reverse("wiki:article-edit", args=[article.slug])
    assert client.get(url).status_code == 200
    client.post(
        url, {"title": "A", "summary": "", "content_md": "two", "status": "published"}
    )
    assert ArticleRevision.objects.filter(article=article).count() == 1


@pytest.mark.django_db
def test_diff_endpoint(client, django_user_model):
    user = django_user_model.objects.create_user("admin", password="pw", is_staff=True)
    client.force_login(user)
    session = client.session
    session["admin_mode"] = True
    session.save()
    article = Article.objects.create(title="A", content_md="one")
    rev = ArticleRevision.objects.create(
        article=article, title="A", content_md="one", author=user
    )
    article.content_md = "two"
    article.save()
    ArticleRevision.objects.create(
        article=article, title="A", content_md="two", author=user
    )
    url = reverse("wiki:article-diff", args=[article.slug, rev.id])
    resp = client.get(url)
    assert resp.status_code == 200
    assert "two" in resp.text


@pytest.mark.django_db
def test_internal_links(client):
    a = Article.objects.create(title="A", content_md="See [[B]]")
    resp = client.get(reverse("wiki:article-detail", args=[a.slug]))
    assert "text-red-600" in resp.text
    Article.objects.create(title="B", content_md="x")
    resp = client.get(reverse("wiki:article-detail", args=[a.slug]))
    assert "text-red-600" in resp.text


@pytest.mark.django_db
def test_internal_links_with_label(client):
    article = Article.objects.create(
        title="A", content_md="[[Střední Evropa|střední Evropě]]"
    )
    resp = client.get(reverse("wiki:article-detail", args=[article.slug]))
    slug = slugify("Střední Evropa")
    url = reverse("wiki:article-detail", args=[slug])
    assert f'href="{url}"' in resp.text
    assert ">střední Evropě</a>" in resp.text


@pytest.mark.django_db
def test_article_suggest_endpoint(client):
    Article.objects.create(title="Alpha", content_md="x")
    resp = client.get(reverse("wiki:article-suggest"), {"q": "Al"})
    assert resp.status_code == 200
    data = resp.json()
    assert any(item["title"] == "Alpha" for item in data)

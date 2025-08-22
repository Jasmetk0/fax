from django.contrib.auth import get_user_model
from django.db import models
from django.utils.text import slugify
from django.urls import reverse

import bleach
import markdown
import re


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    color = models.CharField(max_length=7)
    order = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return self.name


class Article(models.Model):
    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    summary = models.TextField(blank=True)
    content_md = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=10,
        choices=(
            ("draft", "Draft"),
            ("published", "Published"),
        ),
        default="published",
    )
    is_deleted = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, blank=True)
    categories = models.ManyToManyField(
        "Category", through="CategoryArticle", related_name="articles", blank=True
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def content_html(self) -> str:
        def repl(match):
            title = match.group(1)
            slug = slugify(title)
            exists = Article.objects.filter(slug=slug, is_deleted=False).exists()
            url = reverse("wiki:article-detail", args=[slug])
            cls = "" if exists else "text-red-600"
            return f'<a href="{url}" class="{cls}">{title}</a>'

        processed = re.sub(r"\[\[(.+?)\]\]", repl, self.content_md)
        html = markdown.markdown(processed)
        allowed = list(bleach.sanitizer.ALLOWED_TAGS) + ["p", "pre", "span"]
        return bleach.clean(
            html, tags=allowed, attributes={"a": ["href", "class"], "span": ["class"]}
        )

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return self.title


class CategoryArticle(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("category", "article")
        ordering = ["order"]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.category} -> {self.article}"


class ArticleRevision(models.Model):
    article = models.ForeignKey(
        Article, related_name="revisions", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    content_md = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        get_user_model(), null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.article} @ {self.created_at:%Y-%m-%d %H:%M}"

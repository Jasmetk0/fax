from django.db import models
from django.utils.text import slugify

import bleach
import markdown


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return self.name


class Article(models.Model):
    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    content_md = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField(Tag, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def content_html(self) -> str:
        html = markdown.markdown(self.content_md)
        return bleach.clean(html)

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return self.title

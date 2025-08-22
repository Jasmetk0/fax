from django.db import models
from django.utils.text import slugify

import markdown
import bleach


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Article(models.Model):
    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    content_md = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField(Tag, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def content_html(self) -> str:
        html = markdown.markdown(self.content_md or "", extensions=["fenced_code", "tables"])
        # povolené tagy/atributy – můžeš upravit později
        allowed_tags = bleach.sanitizer.ALLOWED_TAGS.union(
            {"p", "pre", "h1", "h2", "h3", "ul", "ol", "li", "code", "blockquote", "hr", "table", "thead", "tbody", "tr", "th", "td"}
        )
        allowed_attrs = {"a": ["href", "title", "rel", "target"]}
        return bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs)

    def __str__(self) -> str:  # pragma: no cover
        return self.title

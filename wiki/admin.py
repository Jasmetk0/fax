from django.contrib import admin
from .models import Article, Tag, Category, CategoryArticle

from . import admin_data  # noqa: F401


class CategoryArticleInline(admin.TabularInline):
    model = CategoryArticle
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "order")
    inlines = [CategoryArticleInline]


admin.site.register(Article)
admin.site.register(Tag)

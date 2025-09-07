from django.contrib import admin

from . import admin_data  # noqa: F401
from .models import Article, Category, CategoryArticle, Tag


class CategoryArticleInline(admin.TabularInline):
    model = CategoryArticle
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "order")
    inlines = [CategoryArticleInline]


admin.site.register(Article)
admin.site.register(Tag)

from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from .models import Article


class ArticleListView(ListView):
    model = Article
    template_name = "wiki/index.html"
    context_object_name = "articles"

    extra_context = {
        "categories": [
            "Geografie",
            "Historie",
            "Sport",
            "Státy",
            "Organizace",
            "Události",
        ]
    }

    def get_queryset(self):
        queryset = super().get_queryset().order_by("-updated_at")
        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(title__icontains=q)
        return queryset


class ArticleDetailView(DetailView):
    model = Article
    template_name = "wiki/article_detail.html"
    context_object_name = "article"
    slug_field = "slug"
    slug_url_kwarg = "slug"


class ArticleCreateView(CreateView):
    model = Article
    fields = ["title", "content_md", "tags"]
    template_name = "wiki/article_form.html"
    success_url = reverse_lazy("wiki:article-list")


class ArticleUpdateView(UpdateView):
    model = Article
    fields = ["title", "content_md", "tags"]
    template_name = "wiki/article_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("wiki:article-list")

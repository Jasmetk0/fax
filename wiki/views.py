from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.forms import inlineformset_factory

from .models import Article, Category, CategoryArticle


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class ArticleListView(ListView):
    model = Article
    template_name = "wiki/index.html"
    context_object_name = "articles"

    def get_queryset(self):
        queryset = super().get_queryset().order_by("-updated_at")
        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(title__icontains=q)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = Category.objects.order_by("order").prefetch_related(
            "categoryarticle_set__article"
        )
        context["categories"] = categories
        return context


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


class CategoryListView(StaffRequiredMixin, ListView):
    model = Category
    template_name = "wiki/category_list.html"
    context_object_name = "categories"


class CategoryCreateView(StaffRequiredMixin, CreateView):
    model = Category
    fields = ["name", "color", "order"]
    template_name = "wiki/category_form.html"
    success_url = reverse_lazy("wiki:category-list")


CategoryArticleFormSet = inlineformset_factory(
    Category, CategoryArticle, fields=("article", "order"), extra=1, can_delete=True
)


class CategoryUpdateView(StaffRequiredMixin, UpdateView):
    model = Category
    fields = ["name", "color", "order"]
    template_name = "wiki/category_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("wiki:category-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = CategoryArticleFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["formset"] = CategoryArticleFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            return super().form_valid(form)
        return self.form_invalid(form)


class CategoryDeleteView(StaffRequiredMixin, DeleteView):
    model = Category
    template_name = "wiki/category_confirm_delete.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("wiki:category-list")

from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    View,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.forms import inlineformset_factory
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
import difflib

from .models import Article, ArticleRevision, Category, CategoryArticle


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class AdminModeRequiredMixin(StaffRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get("admin_mode"):
            return redirect("wiki:article-list")
        return super().dispatch(request, *args, **kwargs)


class ArticleListView(ListView):
    model = Article
    template_name = "wiki/index.html"
    context_object_name = "articles"

    def get_queryset(self):
        queryset = (
            super().get_queryset().filter(is_deleted=False).order_by("-updated_at")
        )
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

    def get_queryset(self):
        return Article.objects.filter(is_deleted=False)


class ArticleCreateView(AdminModeRequiredMixin, CreateView):
    model = Article
    fields = ["title", "summary", "content_md", "status", "tags"]
    template_name = "wiki/article_form.html"

    def form_valid(self, form):
        self.object = form.save()
        ArticleRevision.objects.create(
            article=self.object,
            title=self.object.title,
            summary=self.object.summary,
            content_md=self.object.content_md,
            author=self.request.user,
        )
        return redirect("wiki:article-detail", slug=self.object.slug)


class ArticleUpdateView(AdminModeRequiredMixin, UpdateView):
    model = Article
    fields = ["title", "summary", "content_md", "status", "tags"]
    template_name = "wiki/article_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def form_valid(self, form):
        self.object = form.save()
        ArticleRevision.objects.create(
            article=self.object,
            title=self.object.title,
            summary=self.object.summary,
            content_md=self.object.content_md,
            author=self.request.user,
        )
        return redirect("wiki:article-detail", slug=self.object.slug)


class ArticleDeleteView(AdminModeRequiredMixin, View):
    def post(self, request, slug):
        article = get_object_or_404(Article, slug=slug)
        article.is_deleted = True
        article.save()
        ArticleRevision.objects.create(
            article=article,
            title=article.title,
            summary=article.summary,
            content_md=article.content_md,
            author=request.user,
        )
        return redirect("wiki:article-list")


class ArticleHistoryView(AdminModeRequiredMixin, ListView):
    template_name = "wiki/article_history.html"
    context_object_name = "revisions"

    def get_queryset(self):
        article = get_object_or_404(Article, slug=self.kwargs["slug"])
        return article.revisions.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["article"] = get_object_or_404(Article, slug=self.kwargs["slug"])
        return context


class ArticleRevisionDiffView(AdminModeRequiredMixin, View):
    def get(self, request, slug, rev_id):
        article = get_object_or_404(Article, slug=slug)
        rev = get_object_or_404(ArticleRevision, pk=rev_id, article=article)
        diff = difflib.HtmlDiff().make_table(
            rev.content_md.splitlines(),
            article.content_md.splitlines(),
            fromdesc="rev",
            todesc="current",
        )
        return render(
            request, "wiki/article_diff.html", {"article": article, "diff": diff}
        )


class ArticleRevisionRevertView(AdminModeRequiredMixin, View):
    def post(self, request, slug, rev_id):
        article = get_object_or_404(Article, slug=slug)
        rev = get_object_or_404(ArticleRevision, pk=rev_id, article=article)
        article.title = rev.title
        article.summary = rev.summary
        article.content_md = rev.content_md
        article.save()
        ArticleRevision.objects.create(
            article=article,
            title=article.title,
            summary=article.summary,
            content_md=article.content_md,
            author=request.user,
        )
        return redirect("wiki:article-detail", slug=article.slug)


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


def article_suggest(request):
    q = request.GET.get("q", "")
    articles = Article.objects.filter(title__icontains=q, is_deleted=False)[:5]
    data = [{"title": a.title, "slug": a.slug} for a in articles]
    return JsonResponse(data, safe=False)

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import (
    MatchForm,
    MediaItemForm,
    NewsPostForm,
    PlayerForm,
    RankingEntryForm,
    RankingSnapshotForm,
    TournamentForm,
)
from .models import (
    Match,
    MediaItem,
    NewsPost,
    Player,
    RankingEntry,
    RankingSnapshot,
    Tournament,
)
from .views import _admin_required


@_admin_required
def player_create(request):
    if request.method == "POST":
        form = PlayerForm(request.POST)
        if form.is_valid():
            player = form.save(commit=False)
            player.created_by = player.updated_by = request.user
            player.save()
            messages.success(request, "Saved")
            return redirect("msa:player-list")
    else:
        form = PlayerForm()
    return render(
        request,
        "msa/manage_form.html",
        {
            "form": form,
            "title": "Add Player",
            "cancel_url": reverse("msa:player-list"),
        },
    )


@_admin_required
def player_edit(request, slug):
    player = get_object_or_404(Player, slug=slug)
    if request.method == "POST":
        form = PlayerForm(request.POST, instance=player)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            messages.success(request, "Saved")
            return redirect("msa:player-detail", slug=player.slug)
    else:
        form = PlayerForm(instance=player)
    return render(
        request,
        "msa/manage_form.html",
        {
            "form": form,
            "title": "Edit Player",
            "cancel_url": reverse("msa:player-detail", args=[player.slug]),
        },
    )


@_admin_required
def player_delete(request, slug):
    player = get_object_or_404(Player, slug=slug)
    if request.method == "POST":
        player.delete()
        messages.success(request, "Deleted")
        return redirect("msa:player-list")
    return render(
        request,
        "msa/manage_confirm_delete.html",
        {
            "title": f"Delete {player.name}?",
            "cancel_url": reverse("msa:player-detail", args=[player.slug]),
        },
    )


@_admin_required
def tournament_create(request):
    if request.method == "POST":
        form = TournamentForm(request.POST)
        if form.is_valid():
            t = form.save(commit=False)
            t.created_by = t.updated_by = request.user
            t.save()
            messages.success(request, "Saved")
            return redirect("msa:tournament-list")
    else:
        form = TournamentForm()
    return render(
        request,
        "msa/manage_form.html",
        {
            "form": form,
            "title": "Add Tournament",
            "cancel_url": reverse("msa:tournament-list"),
        },
    )


@_admin_required
def tournament_edit(request, slug):
    tournament = get_object_or_404(Tournament, slug=slug)
    if request.method == "POST":
        form = TournamentForm(request.POST, instance=tournament)
        if form.is_valid():
            t = form.save(commit=False)
            t.updated_by = request.user
            t.save()
            messages.success(request, "Saved")
            return redirect("msa:tournament-detail", slug=tournament.slug)
    else:
        form = TournamentForm(instance=tournament)
    return render(
        request,
        "msa/manage_form.html",
        {
            "form": form,
            "title": "Edit Tournament",
            "cancel_url": reverse("msa:tournament-detail", args=[tournament.slug]),
        },
    )


@_admin_required
def tournament_delete(request, slug):
    tournament = get_object_or_404(Tournament, slug=slug)
    if request.method == "POST":
        tournament.delete()
        messages.success(request, "Deleted")
        return redirect("msa:tournament-list")
    return render(
        request,
        "msa/manage_confirm_delete.html",
        {
            "title": f"Delete {tournament.name}?",
            "cancel_url": reverse("msa:tournament-detail", args=[tournament.slug]),
        },
    )


@_admin_required
def match_create(request):
    tournament_slug = request.GET.get("tournament")
    tournament = (
        get_object_or_404(Tournament, slug=tournament_slug) if tournament_slug else None
    )
    if request.method == "POST":
        form = MatchForm(request.POST)
        if form.is_valid():
            match = form.save(commit=False)
            if tournament:
                match.tournament = tournament
            match.created_by = match.updated_by = request.user
            match.save()
            messages.success(request, "Saved")
            return redirect("msa:tournament-detail", slug=match.tournament.slug)
    else:
        form = MatchForm(initial={"tournament": tournament})
    return render(
        request,
        "msa/manage_form.html",
        {
            "form": form,
            "title": "Add Match",
            "cancel_url": reverse(
                "msa:tournament-detail", args=[tournament.slug] if tournament else []
            ),
        },
    )


@_admin_required
def match_edit(request, pk):
    match = get_object_or_404(Match, pk=pk)
    if request.method == "POST":
        form = MatchForm(request.POST, instance=match)
        if form.is_valid():
            m = form.save(commit=False)
            m.updated_by = request.user
            m.save()
            messages.success(request, "Saved")
            return redirect("msa:tournament-detail", slug=match.tournament.slug)
    else:
        form = MatchForm(instance=match)
    return render(
        request,
        "msa/manage_form.html",
        {
            "form": form,
            "title": "Edit Match",
            "cancel_url": reverse(
                "msa:tournament-detail", args=[match.tournament.slug]
            ),
        },
    )


@_admin_required
def match_delete(request, pk):
    match = get_object_or_404(Match, pk=pk)
    if request.method == "POST":
        slug = match.tournament.slug
        match.delete()
        messages.success(request, "Deleted")
        return redirect("msa:tournament-detail", slug=slug)
    return render(
        request,
        "msa/manage_confirm_delete.html",
        {
            "title": "Delete match?",
            "cancel_url": reverse(
                "msa:tournament-detail", args=[match.tournament.slug]
            ),
        },
    )


@_admin_required
def snapshot_create(request):
    if request.method == "POST":
        form = RankingSnapshotForm(request.POST)
        if form.is_valid():
            snap = form.save(commit=False)
            snap.created_by = snap.updated_by = request.user
            snap.save()
            messages.success(request, "Saved")
            return redirect("msa:rankings")
    else:
        form = RankingSnapshotForm()
    return render(
        request,
        "msa/manage_form.html",
        {
            "form": form,
            "title": "Add Ranking Snapshot",
            "cancel_url": reverse("msa:rankings"),
        },
    )


@_admin_required
def snapshot_edit(request, pk):
    snap = get_object_or_404(RankingSnapshot, pk=pk)
    if request.method == "POST":
        form = RankingSnapshotForm(request.POST, instance=snap)
        if form.is_valid():
            s = form.save(commit=False)
            s.updated_by = request.user
            s.save()
            messages.success(request, "Saved")
            return redirect("msa:rankings")
    else:
        form = RankingSnapshotForm(instance=snap)
    return render(
        request,
        "msa/manage_form.html",
        {
            "form": form,
            "title": "Edit Ranking Snapshot",
            "cancel_url": reverse("msa:rankings"),
        },
    )


@_admin_required
def snapshot_delete(request, pk):
    snap = get_object_or_404(RankingSnapshot, pk=pk)
    if request.method == "POST":
        snap.delete()
        messages.success(request, "Deleted")
        return redirect("msa:rankings")
    return render(
        request,
        "msa/manage_confirm_delete.html",
        {
            "title": "Delete snapshot?",
            "cancel_url": reverse("msa:rankings"),
        },
    )


@_admin_required
def entry_create(request):
    if request.method == "POST":
        form = RankingEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.created_by = entry.updated_by = request.user
            entry.save()
            messages.success(request, "Saved")
            return redirect("msa:rankings")
    else:
        form = RankingEntryForm()
    return render(
        request,
        "msa/manage_form.html",
        {
            "form": form,
            "title": "Add Ranking Entry",
            "cancel_url": reverse("msa:rankings"),
        },
    )


@_admin_required
def entry_edit(request, pk):
    entry = get_object_or_404(RankingEntry, pk=pk)
    if request.method == "POST":
        form = RankingEntryForm(request.POST, instance=entry)
        if form.is_valid():
            e = form.save(commit=False)
            e.updated_by = request.user
            e.save()
            messages.success(request, "Saved")
            return redirect("msa:rankings")
    else:
        form = RankingEntryForm(instance=entry)
    return render(
        request,
        "msa/manage_form.html",
        {
            "form": form,
            "title": "Edit Ranking Entry",
            "cancel_url": reverse("msa:rankings"),
        },
    )


@_admin_required
def entry_delete(request, pk):
    entry = get_object_or_404(RankingEntry, pk=pk)
    if request.method == "POST":
        entry.delete()
        messages.success(request, "Deleted")
        return redirect("msa:rankings")
    return render(
        request,
        "msa/manage_confirm_delete.html",
        {
            "title": "Delete entry?",
            "cancel_url": reverse("msa:rankings"),
        },
    )


@_admin_required
def news_create(request):
    if request.method == "POST":
        form = NewsPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.created_by = post.updated_by = request.user
            post.save()
            messages.success(request, "Saved")
            return redirect("msa:news")
    else:
        form = NewsPostForm()
    return render(
        request,
        "msa/manage_form.html",
        {
            "form": form,
            "title": "Add News",
            "cancel_url": reverse("msa:news"),
        },
    )


@_admin_required
def news_edit(request, slug):
    post = get_object_or_404(NewsPost, slug=slug)
    if request.method == "POST":
        form = NewsPostForm(request.POST, instance=post)
        if form.is_valid():
            p = form.save(commit=False)
            p.updated_by = request.user
            p.save()
            messages.success(request, "Saved")
            return redirect("msa:news-detail", slug=post.slug)
    else:
        form = NewsPostForm(instance=post)
    return render(
        request,
        "msa/manage_form.html",
        {
            "form": form,
            "title": "Edit News",
            "cancel_url": reverse("msa:news-detail", args=[post.slug]),
        },
    )


@_admin_required
def news_delete(request, slug):
    post = get_object_or_404(NewsPost, slug=slug)
    if request.method == "POST":
        post.delete()
        messages.success(request, "Deleted")
        return redirect("msa:news")
    return render(
        request,
        "msa/manage_confirm_delete.html",
        {
            "title": f"Delete {post.title}?",
            "cancel_url": reverse("msa:news-detail", args=[post.slug]),
        },
    )


@_admin_required
def media_create(request):
    if request.method == "POST":
        form = MediaItemForm(request.POST)
        if form.is_valid():
            media = form.save(commit=False)
            media.created_by = media.updated_by = request.user
            media.save()
            messages.success(request, "Saved")
            return redirect("msa:squashtv")
    else:
        form = MediaItemForm()
    return render(
        request,
        "msa/manage_form.html",
        {
            "form": form,
            "title": "Add Media",
            "cancel_url": reverse("msa:squashtv"),
        },
    )


@_admin_required
def media_edit(request, slug):
    media = get_object_or_404(MediaItem, slug=slug)
    if request.method == "POST":
        form = MediaItemForm(request.POST, instance=media)
        if form.is_valid():
            m = form.save(commit=False)
            m.updated_by = request.user
            m.save()
            messages.success(request, "Saved")
            return redirect("msa:squashtv")
    else:
        form = MediaItemForm(instance=media)
    return render(
        request,
        "msa/manage_form.html",
        {
            "form": form,
            "title": "Edit Media",
            "cancel_url": reverse("msa:squashtv"),
        },
    )


@_admin_required
def media_delete(request, slug):
    media = get_object_or_404(MediaItem, slug=slug)
    if request.method == "POST":
        media.delete()
        messages.success(request, "Deleted")
        return redirect("msa:squashtv")
    return render(
        request,
        "msa/manage_confirm_delete.html",
        {
            "title": f"Delete {media.title}?",
            "cancel_url": reverse("msa:squashtv"),
        },
    )

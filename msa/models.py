from django.conf import settings
from django.db import models
from django.utils.text import slugify

from fax_calendar.fields import WoorldDateField


class AuditModel(models.Model):
    """Abstract base model with audit fields."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_updated",
    )

    class Meta:
        abstract = True


class Player(AuditModel):
    HAND_CHOICES = [
        ("right", "Right"),
        ("left", "Left"),
        ("ambi", "Ambidextrous"),
        ("unknown", "Unknown"),
    ]

    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(unique=True, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    nickname = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    birthdate = WoorldDateField(null=True, blank=True)
    handedness = models.CharField(
        max_length=10, choices=HAND_CHOICES, null=True, blank=True
    )
    height = models.IntegerField(null=True, blank=True)
    weight = models.IntegerField(null=True, blank=True)
    turned_pro = WoorldDateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    bio = models.TextField(blank=True)
    photo_url = models.URLField(null=True, blank=True)
    current_rank = models.IntegerField(null=True, blank=True, db_index=True)
    current_points = models.IntegerField(null=True, blank=True)
    rtf_current_rank = models.IntegerField(
        null=True, blank=True, db_index=True, verbose_name="RTF current rank"
    )
    rtf_current_points = models.IntegerField(
        null=True, blank=True, verbose_name="RTF current points"
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 2
            while Player.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def age(self):
        """Age calculation is not implemented for Woorld dates."""
        return None

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class Tournament(AuditModel):
    STATUS_CHOICES = [
        ("upcoming", "Upcoming"),
        ("ongoing", "Ongoing"),
        ("finished", "Finished"),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=50)
    start_date = WoorldDateField()
    end_date = WoorldDateField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    venue = models.CharField(max_length=200, blank=True)
    prize_money = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class Match(AuditModel):
    LIVE_CHOICES = [
        ("scheduled", "Scheduled"),
        ("live", "Live"),
        ("finished", "Finished"),
    ]

    tournament = models.ForeignKey(
        Tournament, on_delete=models.CASCADE, related_name="matches"
    )
    round = models.CharField(max_length=50)
    section = models.CharField(max_length=50, blank=True)
    best_of = models.IntegerField(default=5)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    player1 = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="matches_as_player1"
    )
    player2 = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="matches_as_player2"
    )
    winner = models.ForeignKey(
        Player, null=True, blank=True, on_delete=models.SET_NULL, related_name="wins"
    )
    scoreline = models.CharField(max_length=100, blank=True)
    live_status = models.CharField(
        max_length=20, choices=LIVE_CHOICES, default="scheduled"
    )
    live_p1_points = models.IntegerField(null=True, blank=True)
    live_p2_points = models.IntegerField(null=True, blank=True)
    live_game_no = models.IntegerField(null=True, blank=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.player1} vs {self.player2}"


class RankingSnapshot(AuditModel):
    as_of = WoorldDateField(unique=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return str(self.as_of)


class RankingEntry(AuditModel):
    snapshot = models.ForeignKey(
        RankingSnapshot, on_delete=models.CASCADE, related_name="entries"
    )
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    rank = models.IntegerField()
    points = models.IntegerField()

    class Meta:
        unique_together = ("snapshot", "player")
        ordering = ["rank"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.player} #{self.rank}"


class NewsPost(AuditModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    published_at = models.DateTimeField()
    author = models.CharField(max_length=100)
    excerpt = models.TextField()
    body = models.TextField()
    cover_url = models.URLField(null=True, blank=True)
    is_published = models.BooleanField(default=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.title


class MediaItem(AuditModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    published_at = models.DateTimeField()
    video_url = models.URLField()
    thumbnail_url = models.URLField(null=True, blank=True)
    tags = models.CharField(max_length=200, blank=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.title

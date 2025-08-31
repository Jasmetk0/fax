import math

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


class Season(AuditModel):
    """A single Woorld calendar season."""

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    start_date = WoorldDateField(null=True, blank=True)
    end_date = WoorldDateField(null=True, blank=True)

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
    season = models.ForeignKey(
        Season,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tournaments",
    )
    category = models.ForeignKey(
        "Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tournaments",
    )
    season_category = models.ForeignKey(
        "CategorySeason",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tournaments",
    )
    start_date = WoorldDateField(null=True, blank=True)
    end_date = WoorldDateField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    venue = models.CharField(max_length=200, null=True, blank=True)
    prize_money = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, null=True, blank=True
    )

    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        ENTRY_OPEN = "entry_open", "Entry Open"
        ENTRY_LOCKED = "entry_locked", "Entry Locked"
        DRAWN = "drawn", "Drawn"
        LIVE = "live", "Live"
        COMPLETE = "complete", "Complete"

    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)
    draw_policy = models.CharField(max_length=20, default="single_elim")
    draw_size = models.IntegerField(default=0)
    seeds_count = models.IntegerField(default=0)
    qualifiers_count = models.IntegerField(default=0)
    lucky_losers = models.IntegerField(default=0)
    seeding_method = models.CharField(
        max_length=20,
        choices=[
            ("ranking_snapshot", "Ranking snapshot"),
            ("manual", "Manual"),
            ("random", "Random"),
            ("local_rating", "Local rating"),
        ],
        default="manual",
    )
    seeding_rank_date = WoorldDateField(null=True, blank=True)
    allow_manual_bracket_edits = models.BooleanField(default=True)
    flex_mode = models.BooleanField(default=False)
    entry_deadline = WoorldDateField(null=True, blank=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class TournamentEntry(AuditModel):
    class EntryType(models.TextChoices):
        DA = "DA", "Direct Acceptance"
        Q = "Q", "Qualifier"
        WC = "WC", "Wildcard"
        LL = "LL", "Lucky Loser"
        ALT = "ALT", "Alternate"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        WITHDRAWN = "withdrawn", "Withdrawn"
        REPLACED = "replaced", "Replaced"

    tournament = models.ForeignKey(
        Tournament, on_delete=models.CASCADE, related_name="entries"
    )
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    seed = models.IntegerField(null=True, blank=True)
    entry_type = models.CharField(
        max_length=3, choices=EntryType.choices, default=EntryType.DA
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    position = models.IntegerField(null=True, blank=True)
    seed_locked = models.BooleanField(default=False)
    origin_note = models.CharField(max_length=20, blank=True)
    origin_match = models.ForeignKey(
        "Match",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="origin_entries",
    )

    class Meta:
        unique_together = ("tournament", "player")
        ordering = ["seed", "player__name"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.player} in {self.tournament}"


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
    video_url = models.URLField(blank=True, null=True)

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


class PointsTable(AuditModel):
    name = models.CharField(max_length=100)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class PointsRow(AuditModel):
    points_table = models.ForeignKey(
        PointsTable, on_delete=models.CASCADE, related_name="rows"
    )
    round_code = models.CharField(max_length=10)
    points = models.IntegerField()
    co_sanction_pct = models.IntegerField(default=100)

    class Meta:
        unique_together = ("points_table", "round_code")

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.points_table} {self.round_code}"


class PrizeTable(AuditModel):
    name = models.CharField(max_length=100)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class PrizeRow(AuditModel):
    prize_table = models.ForeignKey(
        PrizeTable, on_delete=models.CASCADE, related_name="rows"
    )
    round_code = models.CharField(max_length=10)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ("prize_table", "round_code")

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.prize_table} {self.round_code}"


class BracketPolicy(AuditModel):
    name = models.CharField(max_length=100)
    draw_size = models.IntegerField()
    format = models.CharField(
        max_length=50,
        choices=[("playoff", "Play-off")],
        null=True,
        blank=True,
    )

    def generate_round_labels(self):
        rounds = []
        n = self.draw_size
        order = 1
        while True:
            if n > 8:
                label = f"Round of {n}"
            elif n == 8:
                label = "Quarter Final"
            elif n == 4:
                label = "Semi Final"
            elif n == 2:
                label = "Final"
            elif n == 1:
                label = "Winner"
            rounds.append((order, label))
            if n <= 1:
                break
            next_power = 2 ** int(math.floor(math.log2(n)))
            n = n // 2 if n == next_power else next_power
            order += 1
        return rounds

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class SeedingPolicy(AuditModel):
    name = models.CharField(max_length=100)
    config = models.JSONField(default=dict)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class Category(AuditModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 2
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class CategorySeason(AuditModel):
    season = models.ForeignKey(
        Season, on_delete=models.CASCADE, related_name="category_seasons"
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="category_seasons"
    )
    label = models.CharField(max_length=100, db_index=True)
    points_table = models.ForeignKey(
        PointsTable, null=True, blank=True, on_delete=models.SET_NULL
    )
    prize_table = models.ForeignKey(
        PrizeTable, null=True, blank=True, on_delete=models.SET_NULL
    )
    bracket_policy = models.ForeignKey(
        BracketPolicy, null=True, blank=True, on_delete=models.SET_NULL
    )
    seeding_policy = models.ForeignKey(
        SeedingPolicy, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        unique_together = ("season", "category")

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.season} - {self.category}"


class ScoringRule(AuditModel):
    """Placeholder scoring rule model."""

    name = models.CharField(max_length=100)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class DrawTemplate(AuditModel):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    version = models.IntegerField(default=1)
    dsl_json = models.JSONField()

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class EventBrand(AuditModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 2
            while EventBrand.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class EventEdition(AuditModel):
    brand = models.ForeignKey(
        EventBrand, on_delete=models.CASCADE, related_name="editions"
    )
    season = models.ForeignKey(
        Season, on_delete=models.CASCADE, related_name="event_editions"
    )
    name = models.CharField(max_length=200)
    category_season = models.ForeignKey(
        "CategorySeason",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="event_editions",
    )
    start_date = WoorldDateField(null=True, blank=True)
    end_date = WoorldDateField(null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    scoring_rules = models.ForeignKey(
        "ScoringRule", null=True, blank=True, on_delete=models.SET_NULL
    )
    best_of = models.IntegerField(default=5)
    sanction_status = models.CharField(max_length=20, blank=True)
    points_eligible = models.BooleanField(default=True)
    draw_template = models.ForeignKey(
        "DrawTemplate", null=True, blank=True, on_delete=models.SET_NULL
    )
    uses_snapshot = models.ForeignKey(
        RankingSnapshot, null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class EventPhase(AuditModel):
    TYPE_CHOICES = [
        ("single_elim", "Single Elimination"),
        ("qualifying", "Qualifying"),
        ("round_robin", "Round Robin"),
        ("swiss", "Swiss"),
        ("placement", "Placement"),
        ("exhibition", "Exhibition"),
    ]

    event = models.ForeignKey(
        EventEdition, on_delete=models.CASCADE, related_name="phases"
    )
    order = models.IntegerField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    name = models.CharField(max_length=100)
    config = models.JSONField(default=dict)
    points_table = models.ForeignKey(
        PointsTable, null=True, blank=True, on_delete=models.SET_NULL
    )
    scoring_rules = models.ForeignKey(
        ScoringRule, null=True, blank=True, on_delete=models.SET_NULL
    )
    seeding_policy = models.ForeignKey(
        SeedingPolicy, null=True, blank=True, on_delete=models.SET_NULL
    )
    uses_snapshot = models.ForeignKey(
        RankingSnapshot, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        unique_together = ("event", "order")
        ordering = ["order"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.event} - {self.name}"


class PhaseRound(AuditModel):
    phase = models.ForeignKey(
        EventPhase, on_delete=models.CASCADE, related_name="rounds"
    )
    order = models.IntegerField()
    code = models.CharField(max_length=10)
    label = models.CharField(max_length=100)
    entrants = models.IntegerField()
    matches = models.IntegerField()
    best_of = models.IntegerField()

    class Meta:
        unique_together = ("phase", "order")
        ordering = ["order"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.phase} - {self.code}"


class EventMatch(AuditModel):
    phase = models.ForeignKey(
        EventPhase, on_delete=models.CASCADE, related_name="matches"
    )
    round = models.ForeignKey(
        PhaseRound, on_delete=models.CASCADE, related_name="round_matches"
    )
    order = models.IntegerField()
    a_player = models.ForeignKey(
        Player,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="event_matches_as_a",
    )
    b_player = models.ForeignKey(
        Player,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="event_matches_as_b",
    )
    a_source = models.CharField(max_length=40, null=True, blank=True)
    b_source = models.CharField(max_length=40, null=True, blank=True)
    a_score = models.IntegerField(null=True, blank=True)
    b_score = models.IntegerField(null=True, blank=True)
    winner = models.ForeignKey(
        Player,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="event_match_wins",
    )

    class Meta:
        unique_together = ("phase", "round", "order")
        ordering = ["phase", "round", "order"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.round.code} M{self.order}"


class AdvancementEdge(AuditModel):
    phase = models.ForeignKey(
        EventPhase, on_delete=models.CASCADE, related_name="edges"
    )
    from_ref = models.CharField(max_length=40)
    to_ref = models.CharField(max_length=40)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.from_ref} -> {self.to_ref}"


class EventEntry(AuditModel):
    ENTRY_CHOICES = [
        ("direct", "Direct"),
        ("qualifier", "Qualifier"),
        ("wildcard", "Wildcard"),
        ("protected", "Protected"),
    ]

    event = models.ForeignKey(
        EventEdition, on_delete=models.CASCADE, related_name="entries"
    )
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="event_entries"
    )
    entry_type = models.CharField(max_length=20, choices=ENTRY_CHOICES)
    seed_no = models.IntegerField(null=True, blank=True)
    club_id = models.IntegerField(null=True, blank=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.player} @ {self.event}"

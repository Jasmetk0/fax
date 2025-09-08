from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

"""
SOFT SCHEMA (MVP):
- Co nejméně povinných polí: všude, kde to dává smysl, je `null=True, blank=True`.
- Cílem je, aby migrace/seedování nikdy nezastavily rozvoj. Později zpřísníme.
"""


class TournamentState(models.TextChoices):
    REG = "REG", "Registration"
    QUAL = "QUAL", "Qualification"
    MD = "MD", "Main Draw"
    COMPLETE = "COMPLETE", "Complete"


class SeedingSource(models.TextChoices):
    SNAPSHOT = "SNAPSHOT", "Snapshot"
    CURRENT = "CURRENT", "Current"
    NONE = "NONE", "None"


class EntryType(models.TextChoices):
    DA = "DA", "Direct Acceptance"
    Q = "Q", "Qualifier"
    ALT = "ALT", "Alternate/Reserve"
    WC = "WC", "Wild Card"
    QWC = "QWC", "Qual Wild Card"
    LL = "LL", "Lucky Loser"


class EntryStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class Phase(models.TextChoices):
    QUAL = "QUAL", "Qualification"
    MD = "MD", "Main Draw"


class MatchState(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SCHEDULED = "SCHEDULED", "Scheduled"
    DONE = "DONE", "Finished"


class RankingScope(models.TextChoices):
    ROLLING_ONLY = "ROLLING_ONLY", "Rolling only"
    SEASON = "SEASON", "Season"
    BOTH = "BOTH", "Both"


class Season(models.Model):
    name = models.CharField(max_length=32, unique=True, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    best_n = models.PositiveSmallIntegerField(default=16, null=True, blank=True)

    class Meta:
        ordering = ["start_date"]

    def __str__(self):
        return self.name or "<Season>"


class Category(models.Model):
    name = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name or "<Category>"


class CategorySeason(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=True, blank=True)
    season = models.ForeignKey(Season, on_delete=models.PROTECT, null=True, blank=True)
    draw_size = models.PositiveSmallIntegerField(
        choices=[(16, "16"), (32, "32"), (64, "64")], null=True, blank=True
    )

    md_seeds_count = models.PositiveSmallIntegerField(default=8, null=True, blank=True)
    qualifiers_count = models.PositiveSmallIntegerField(default=0, null=True, blank=True)
    qual_rounds = models.PositiveSmallIntegerField(default=0, null=True, blank=True)
    qual_seeds_per_bracket = models.PositiveSmallIntegerField(default=0, null=True, blank=True)

    wc_slots_default = models.PositiveSmallIntegerField(default=0, null=True, blank=True)
    q_wc_slots_default = models.PositiveSmallIntegerField(default=0, null=True, blank=True)

    scoring_md = models.JSONField(default=dict, blank=True, null=True)
    scoring_qual_win = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        # ponecháme unikátnost, ale protože hodnoty mohou být NULL, DB obvykle
        # dovolí víc NULL řádků; pro MVP nevadí. Později zpřísníme.
        constraints = [
            models.UniqueConstraint(
                fields=["category", "season", "draw_size"], name="uniq_category_season_drawsize"
            )
        ]

    def __str__(self):
        return f"{self.category or '?'} {self.season or '?'} (draw {self.draw_size or '?'} )"


class Player(models.Model):
    name = models.CharField(max_length=120, null=True, blank=True)
    country = models.CharField(max_length=3, blank=True, null=True, default=None)  # ISO3 volitelné

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name or "<Player>"


class PlayerLicense(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, null=True, blank=True)
    season = models.ForeignKey(Season, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["player", "season"], name="uniq_player_season_license")
        ]

    def __str__(self):
        return f"{self.player or '?'} @ {self.season or '?'}"


class Tournament(models.Model):
    season = models.ForeignKey(Season, on_delete=models.PROTECT, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=True, blank=True)
    category_season = models.ForeignKey(
        CategorySeason, on_delete=models.PROTECT, null=True, blank=True
    )

    name = models.CharField(max_length=120, null=True, blank=True)
    slug = models.SlugField(max_length=140, unique=True, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    draw_size = models.PositiveSmallIntegerField(null=True, blank=True)

    q_best_of = models.PositiveSmallIntegerField(default=3, null=True, blank=True)
    md_best_of = models.PositiveSmallIntegerField(default=5, null=True, blank=True)

    wc_slots = models.PositiveSmallIntegerField(null=True, blank=True)
    q_wc_slots = models.PositiveSmallIntegerField(null=True, blank=True)

    third_place_enabled = models.BooleanField(default=False)

    seeding_source = models.CharField(
        max_length=16,
        choices=SeedingSource.choices,
        default=SeedingSource.SNAPSHOT,
        null=True,
        blank=True,
    )
    snapshot_label = models.CharField(max_length=120, blank=True, null=True, default=None)

    rng_seed_active = models.BigIntegerField(default=0, null=True, blank=True)
    state = models.CharField(
        max_length=12,
        choices=TournamentState.choices,
        default=TournamentState.REG,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ["-start_date", "name"]

    def __str__(self):
        return self.name or self.slug or "<Tournament>"


class TournamentEntry(models.Model):
    Status = EntryStatus
    tournament = models.ForeignKey(
        Tournament, on_delete=models.CASCADE, related_name="entries", null=True, blank=True
    )
    player = models.ForeignKey(Player, on_delete=models.PROTECT, null=True, blank=True)

    entry_type = models.CharField(
        max_length=8, choices=EntryType.choices, default=EntryType.DA, null=True, blank=True
    )
    seed = models.PositiveSmallIntegerField(null=True, blank=True)
    wr_snapshot = models.PositiveIntegerField(null=True, blank=True)  # WR pro seeding/snapshot

    status = models.CharField(
        max_length=12,
        choices=EntryStatus.choices,
        default=EntryStatus.ACTIVE,
        null=True,
        blank=True,
    )
    position = models.PositiveIntegerField(null=True, blank=True)

    is_wc = models.BooleanField(default=False, null=True, blank=True)
    is_qwc = models.BooleanField(default=False, null=True, blank=True)
    promoted_by_wc = models.BooleanField(default=False, null=True, blank=True)
    promoted_by_qwc = models.BooleanField(default=False, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tournament", "status"]),
            models.Index(fields=["tournament", "entry_type"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tournament", "player"],
                condition=models.Q(status=EntryStatus.ACTIVE),
                name="uniq_active_entry_per_player_tournament",
            ),
            models.UniqueConstraint(
                fields=["tournament", "position"],
                condition=models.Q(status=EntryStatus.ACTIVE),
                name="uniq_active_position_per_tournament",
            ),
        ]

    def __str__(self):
        return f"{self.player or '?'} @ {self.tournament or '?'} [{self.entry_type or '-'}]"


class Match(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, null=True, blank=True)
    phase = models.CharField(max_length=8, choices=Phase.choices, null=True, blank=True)
    round_name = models.CharField(
        max_length=16, null=True, blank=True
    )  # "R64","R32","R16","QF","SF","F","3P" atd.

    round = models.CharField(max_length=16, null=True, blank=True)
    position = models.PositiveIntegerField(null=True, blank=True)

    slot_top = models.PositiveIntegerField(null=True, blank=True)
    slot_bottom = models.PositiveIntegerField(null=True, blank=True)

    player_top = models.ForeignKey(
        Player, on_delete=models.PROTECT, related_name="matches_as_top", null=True, blank=True
    )
    player_bottom = models.ForeignKey(
        Player, on_delete=models.PROTECT, related_name="matches_as_bottom", null=True, blank=True
    )

    player1 = models.ForeignKey(
        Player, on_delete=models.PROTECT, related_name="matches_as_player1", null=True, blank=True
    )
    player2 = models.ForeignKey(
        Player, on_delete=models.PROTECT, related_name="matches_as_player2", null=True, blank=True
    )

    winner = models.ForeignKey(
        Player, on_delete=models.PROTECT, related_name="wins", null=True, blank=True
    )

    best_of = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1)], null=True, blank=True
    )
    win_by_two = models.BooleanField(default=True)

    score = models.JSONField(
        default=dict, blank=True, null=True
    )  # {"sets": [[11,8],...], "special": "WO/RET/DQ"}

    state = models.CharField(
        max_length=12, choices=MatchState.choices, default=MatchState.PENDING, null=True, blank=True
    )
    needs_review = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["tournament", "phase", "round_name"]),
            models.Index(fields=["tournament", "round"]),
            models.Index(fields=["tournament", "position"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tournament", "phase", "round_name", "slot_top", "slot_bottom"],
                name="uniq_match_slot_in_round",
            ),
            models.UniqueConstraint(
                fields=["tournament", "round", "position"],
                name="uniq_match_tournament_round_position",
            ),
        ]

    def __str__(self):
        return f"{getattr(self.tournament, 'slug', None) or '?'}:{self.phase or '?'}:{self.round_name or '?'}"


class Schedule(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, null=True, blank=True)
    play_date = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(null=True, blank=True)
    match = models.OneToOneField(
        Match, on_delete=models.CASCADE, related_name="schedule", null=True, blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tournament", "play_date", "order"], name="uniq_tournament_day_order"
            )
        ]
        ordering = ["play_date", "order"]


class Snapshot(models.Model):
    class SnapshotType(models.TextChoices):
        CONFIRM_QUAL = "CONFIRM_QUAL", "Confirm Qualification"
        CONFIRM_MD = "CONFIRM_MD", "Confirm Main Draw"
        GENERATE = "GENERATE", "Generate"
        REGENERATE = "REGENERATE", "Regenerate"
        MANUAL = "MANUAL", "Manual Edit"
        REOPEN = "REOPEN", "Reopen"
        BRUTAL = "BRUTAL", "Brutal Reset"

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=16, choices=SnapshotType.choices, null=True, blank=True)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class RankingAdjustment(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, null=True, blank=True)
    scope = models.CharField(
        max_length=16,
        choices=RankingScope.choices,
        default=RankingScope.ROLLING_ONLY,
        null=True,
        blank=True,
    )

    points_delta = models.IntegerField(default=0, null=True, blank=True)
    start_monday = models.DateField(null=True, blank=True)
    duration_weeks = models.PositiveSmallIntegerField(default=61, null=True, blank=True)

    best_n_penalty = models.SmallIntegerField(
        default=0, null=True, blank=True
    )  # např. -1 na X týdnů

    class Meta:
        ordering = ["-start_monday", "-duration_weeks"]

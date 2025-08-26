"""Data models for the MMA app."""

from django.db import models


class Organization(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=50)

    class Meta:
        indexes = [models.Index(fields=["slug"])]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class WeightClass(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=50)
    limit_kg = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        indexes = [models.Index(fields=["slug"])]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class Venue(models.Model):
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.name} ({self.city})"


class Event(models.Model):
    slug = models.SlugField(unique=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="events"
    )
    name = models.CharField(max_length=200)
    date_start = models.DateTimeField()
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="events")
    is_completed = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["date_start"]),
            models.Index(fields=["organization"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class Fighter(models.Model):
    slug = models.SlugField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    nickname = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100)
    stance = models.CharField(max_length=50, blank=True)
    height_cm = models.PositiveIntegerField(null=True, blank=True)
    reach_cm = models.PositiveIntegerField(null=True, blank=True)
    birthdate = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["slug"])]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.first_name} {self.last_name}"


class Bout(models.Model):
    class Result(models.TextChoices):
        RED = "red", "Red"
        BLUE = "blue", "Blue"
        DRAW = "draw", "Draw"
        NC = "nc", "No Contest"
        PENDING = "pending", "Pending"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="bouts")
    weight_class = models.ForeignKey(
        WeightClass, on_delete=models.CASCADE, related_name="bouts"
    )
    fighter_red = models.ForeignKey(
        Fighter, on_delete=models.CASCADE, related_name="bouts_as_red"
    )
    fighter_blue = models.ForeignKey(
        Fighter, on_delete=models.CASCADE, related_name="bouts_as_blue"
    )
    result = models.CharField(
        max_length=10, choices=Result.choices, default=Result.PENDING
    )
    method = models.CharField(max_length=100, blank=True)
    round = models.PositiveSmallIntegerField(null=True, blank=True)
    time = models.CharField(max_length=10, blank=True)
    is_title_fight = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["event"]),
            models.Index(fields=["weight_class"]),
            models.Index(fields=["fighter_red"]),
            models.Index(fields=["fighter_blue"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.fighter_red} vs {self.fighter_blue}"


class Ranking(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="rankings"
    )
    weight_class = models.ForeignKey(
        WeightClass, on_delete=models.CASCADE, related_name="rankings"
    )
    position = models.PositiveSmallIntegerField()
    fighter = models.ForeignKey(
        Fighter, on_delete=models.CASCADE, related_name="rankings"
    )
    date_effective = models.DateField()

    class Meta:
        unique_together = (
            "organization",
            "weight_class",
            "position",
            "date_effective",
        )
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["weight_class"]),
            models.Index(fields=["date_effective"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.organization} {self.weight_class} #{self.position}"


class NewsItem(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    summary = models.TextField()
    content = models.TextField()
    source_url = models.URLField(blank=True)
    published_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["published_at"])]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.title

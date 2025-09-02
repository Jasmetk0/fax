from django.db import models


class Player(models.Model):
    name = models.CharField(max_length=100)
    country = models.ForeignKey(
        "Country", on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

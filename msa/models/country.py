from django.db import models


class Country(models.Model):
    name = models.CharField(max_length=100)
    iso2 = models.CharField(max_length=2, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

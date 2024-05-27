from django.db import models


class Conference(models.Model):
    name = models.CharField(blank=True, null=True, max_length=16)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "conference"


class DimDate(models.Model):
    date = models.DateTimeField(primary_key=True)
    season = models.CharField(blank=True, null=True, max_length=16)
    season_phase = models.CharField(blank=True, null=True, max_length=16)

    def __str__(self):
        display_date = self.date.strftime("%Y-%m-%d")
        return display_date

    class Meta:
        db_table = "dim_date"
        ordering = ["-date"]
        verbose_name = "Date"
        verbose_name_plural = "Dates"


class Division(models.Model):
    name = models.CharField(blank=True, null=True, max_length=16)
    conference = models.ForeignKey(Conference, models.DO_NOTHING, blank=True, null=True)

    def __str__(self):
        display_name = f"{self.conference} - {self.name}"
        return display_name

    class Meta:
        db_table = "division"
        ordering = ["conference", "name"]


class Season(models.Model):
    season = models.CharField(primary_key=True, max_length=8)
    current_yn = models.BooleanField()

    def __str__(self):
        return self.season

    class Meta:
        db_table = "season"


class Team(models.Model):
    name = models.CharField(blank=True, null=True, max_length=32)
    division = models.ForeignKey(Division, models.DO_NOTHING, blank=True, null=True)
    year_founded = models.IntegerField(blank=True, null=True)
    franchise = models.ForeignKey("Franchise", models.DO_NOTHING, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "team"
        ordering = ["name"]


class Arena(models.Model):
    arena = models.CharField(db_column="Arena", max_length=64)
    latitude = models.IntegerField(db_column="Latitude", blank=True, null=True)
    longitude = models.IntegerField(db_column="Longitude", blank=True, null=True)
    team = models.ForeignKey(Team, models.DO_NOTHING, blank=True, null=True, db_column="Team")
    capacity = models.IntegerField(db_column="Capacity", blank=True, null=True)
    opened = models.IntegerField(db_column="Opened", blank=True, null=True)
    closed = models.IntegerField(db_column="Closed", blank=True, null=True)

    def __str__(self):
        return self.arena

    class Meta:
        db_table = "arena"


class Franchise(models.Model):
    franchise = models.CharField(db_column="Franchise", max_length=64)
    year_founded = models.IntegerField(db_column="Year_Founded", blank=True, null=True)

    def __str__(self):
        return self.franchise

    class Meta:
        db_table = "franchise"
        ordering = ["franchise"]
        verbose_name = "Franchise"
        verbose_name_plural = "Franchises"

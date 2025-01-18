from django.contrib import admin

from .models import Arena, Conference, DimDate, Division, Season, Team, Franchise, TeamDatePoint


@admin.register(Arena)
class ArenaAdmin(admin.ModelAdmin):
    list_display = ("arena", "team")
    list_filter = ("team",)
    ordering = ("arena",)


admin.site.register(Conference)
admin.site.register(Franchise)


@admin.register(DimDate)
class DimDateAdmin(admin.ModelAdmin):
    list_display = ("date", "season", "season_phase")
    list_filter = ("season", "season_phase")


admin.site.register(Division)
admin.site.register(Season)
admin.site.register(TeamDatePoint)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "division", "year_founded")
    list_filter = (
        "division",
        "franchise",
    )
    search_fields = ("name",)
    ordering = ("name",)

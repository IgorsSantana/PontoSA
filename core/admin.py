from django.contrib import admin
from .models import Team, Player, Game, PlayerGameStats, BetSuggestion

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'abbreviation', 'conference', 'division')
    search_fields = ('name', 'city', 'abbreviation')
    list_filter = ('conference', 'division')

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'team', 'position')
    search_fields = ('first_name', 'last_name')
    list_filter = ('team', 'position')
    raw_id_fields = ('team',)

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('date', 'home_team', 'away_team', 'home_score', 'away_score', 'status')
    search_fields = ('home_team__name', 'away_team__name')
    list_filter = ('status', 'season')
    raw_id_fields = ('home_team', 'away_team')
    date_hierarchy = 'date'

@admin.register(PlayerGameStats)
class PlayerGameStatsAdmin(admin.ModelAdmin):
    list_display = ('player', 'game', 'points', 'rebounds', 'assists')
    search_fields = ('player__first_name', 'player__last_name')
    list_filter = ('game__date',)
    raw_id_fields = ('player', 'game')

@admin.register(BetSuggestion)
class BetSuggestionAdmin(admin.ModelAdmin):
    list_display = ('player', 'game', 'market', 'line', 'suggestion', 'confidence')
    search_fields = ('player__first_name', 'player__last_name')
    list_filter = ('market', 'suggestion', 'confidence', 'game__date')
    raw_id_fields = ('player', 'game')

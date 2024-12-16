from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Count
from core.models import Team, Player, Game, PlayerGameStats
from .serializers import (
    TeamSerializer,
    PlayerSerializer,
    GameSerializer,
    PlayerGameStatsSerializer
)

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        team = self.get_object()
        home_games = Game.objects.filter(home_team=team)
        away_games = Game.objects.filter(away_team=team)
        
        stats = {
            'total_games': home_games.count() + away_games.count(),
            'home_wins': home_games.filter(home_score__gt=models.F('away_score')).count(),
            'away_wins': away_games.filter(away_score__gt=models.F('home_score')).count(),
            'points_per_game': PlayerGameStats.objects.filter(team=team).aggregate(
                avg_points=Avg('points')
            )['avg_points']
        }
        return Response(stats)

class PlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        player = self.get_object()
        stats = PlayerGameStats.objects.filter(player=player).aggregate(
            games_played=Count('id'),
            avg_points=Avg('points'),
            avg_rebounds=Avg('rebounds'),
            avg_assists=Avg('assists')
        )
        return Response(stats)

class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer

    def get_queryset(self):
        queryset = Game.objects.all()
        season = self.request.query_params.get('season', None)
        team = self.request.query_params.get('team', None)

        if season:
            queryset = queryset.filter(season=season)
        if team:
            queryset = queryset.filter(
                models.Q(home_team__id=team) | models.Q(away_team__id=team)
            )
        return queryset

class PlayerGameStatsViewSet(viewsets.ModelViewSet):
    queryset = PlayerGameStats.objects.all()
    serializer_class = PlayerGameStatsSerializer

    def get_queryset(self):
        queryset = PlayerGameStats.objects.all()
        player = self.request.query_params.get('player', None)
        game = self.request.query_params.get('game', None)
        team = self.request.query_params.get('team', None)

        if player:
            queryset = queryset.filter(player__id=player)
        if game:
            queryset = queryset.filter(game__id=game)
        if team:
            queryset = queryset.filter(team__id=team)
        return queryset

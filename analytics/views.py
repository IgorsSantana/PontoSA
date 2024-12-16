from django.db.models import Avg, Count, F, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from core.models import Team, Player, Game, PlayerGameStats

class TeamAnalytics(APIView):
    def get(self, request, team_id):
        team = Team.objects.get(id=team_id)
        
        # Últimos 10 jogos
        recent_games = Game.objects.filter(
            Q(home_team=team) | Q(away_team=team)
        ).order_by('-date')[:10]
        
        # Estatísticas gerais
        home_games = Game.objects.filter(home_team=team)
        away_games = Game.objects.filter(away_team=team)
        
        stats = {
            'team_name': str(team),
            'recent_form': [
                {
                    'date': game.date,
                    'opponent': str(game.away_team if game.home_team == team else game.home_team),
                    'result': 'W' if (
                        (game.home_team == team and game.home_score > game.away_score) or
                        (game.away_team == team and game.away_score > game.home_score)
                    ) else 'L',
                    'score': f"{game.home_score}-{game.away_score}"
                }
                for game in recent_games
            ],
            'season_stats': {
                'total_games': home_games.count() + away_games.count(),
                'home_record': {
                    'wins': home_games.filter(home_score__gt=F('away_score')).count(),
                    'losses': home_games.filter(home_score__lt=F('away_score')).count()
                },
                'away_record': {
                    'wins': away_games.filter(away_score__gt=F('home_score')).count(),
                    'losses': away_games.filter(away_score__lt=F('home_score')).count()
                }
            }
        }
        
        return Response(stats)

class PlayerAnalytics(APIView):
    def get(self, request, player_id):
        player = Player.objects.get(id=player_id)
        
        # Últimos 10 jogos
        recent_stats = PlayerGameStats.objects.filter(
            player=player
        ).order_by('-game__date')[:10]
        
        # Médias da temporada
        season_averages = PlayerGameStats.objects.filter(
            player=player
        ).aggregate(
            games_played=Count('id'),
            ppg=Avg('points'),
            rpg=Avg('rebounds'),
            apg=Avg('assists'),
            spg=Avg('steals'),
            bpg=Avg('blocks'),
            fg_pct=Avg(F('field_goals_made') * 100.0 / F('field_goals_attempted')),
            three_pct=Avg(F('three_pointers_made') * 100.0 / F('three_pointers_attempted')),
            ft_pct=Avg(F('free_throws_made') * 100.0 / F('free_throws_attempted'))
        )
        
        stats = {
            'player_name': str(player),
            'team': str(player.team),
            'recent_games': [
                {
                    'date': stat.game.date,
                    'opponent': str(stat.game.away_team if stat.game.home_team == stat.team else stat.game.home_team),
                    'minutes': stat.minutes,
                    'points': stat.points,
                    'rebounds': stat.rebounds,
                    'assists': stat.assists
                }
                for stat in recent_stats
            ],
            'season_averages': season_averages
        }
        
        return Response(stats)

class GamePrediction(APIView):
    def get(self, request, home_team_id, away_team_id):
        home_team = Team.objects.get(id=home_team_id)
        away_team = Team.objects.get(id=away_team_id)
        
        # Análise básica baseada nos últimos 10 jogos
        home_recent = Game.objects.filter(
            Q(home_team=home_team) | Q(away_team=home_team)
        ).order_by('-date')[:10]
        
        away_recent = Game.objects.filter(
            Q(home_team=away_team) | Q(away_team=away_team)
        ).order_by('-date')[:10]
        
        # Histórico de confrontos diretos
        head_to_head = Game.objects.filter(
            Q(home_team=home_team, away_team=away_team) |
            Q(home_team=away_team, away_team=home_team)
        ).order_by('-date')[:5]
        
        analysis = {
            'matchup': f"{home_team} vs {away_team}",
            'home_team_form': [
                {
                    'date': game.date,
                    'opponent': str(game.away_team if game.home_team == home_team else game.home_team),
                    'result': 'W' if (
                        (game.home_team == home_team and game.home_score > game.away_score) or
                        (game.away_team == home_team and game.away_score > game.home_score)
                    ) else 'L'
                }
                for game in home_recent
            ],
            'away_team_form': [
                {
                    'date': game.date,
                    'opponent': str(game.away_team if game.home_team == away_team else game.home_team),
                    'result': 'W' if (
                        (game.home_team == away_team and game.home_score > game.away_score) or
                        (game.away_team == away_team and game.away_score > game.home_score)
                    ) else 'L'
                }
                for game in away_recent
            ],
            'head_to_head': [
                {
                    'date': game.date,
                    'score': f"{game.home_score}-{game.away_score}",
                    'winner': str(game.home_team if game.home_score > game.away_score else game.away_team)
                }
                for game in head_to_head
            ]
        }
        
        return Response(analysis)

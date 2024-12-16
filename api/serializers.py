from rest_framework import serializers
from core.models import Team, Player, Game, PlayerGameStats

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'

class PlayerSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = Player
        fields = '__all__'

class GameSerializer(serializers.ModelSerializer):
    home_team_name = serializers.CharField(source='home_team.name', read_only=True)
    away_team_name = serializers.CharField(source='away_team.name', read_only=True)

    class Meta:
        model = Game
        fields = '__all__'

class PlayerGameStatsSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source='player.__str__', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    game_date = serializers.DateField(source='game.date', read_only=True)

    class Meta:
        model = PlayerGameStats
        fields = '__all__' 
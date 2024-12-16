from django.db import models
from django.utils import timezone

class Team(models.Model):
    team_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=10)
    conference = models.CharField(max_length=50)
    division = models.CharField(max_length=50)
    logo_url = models.URLField(max_length=500, null=True, blank=True)

    def __str__(self):
        return f"{self.city} {self.name}"

    class Meta:
        ordering = ['name']

class Player(models.Model):
    player_id = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='players')
    position = models.CharField(max_length=50)
    height = models.CharField(max_length=20, null=True, blank=True)
    weight = models.CharField(max_length=20, null=True, blank=True)
    photo_url = models.URLField(max_length=500, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ['last_name', 'first_name']

class Game(models.Model):
    GAME_STATUS_CHOICES = [
        ('Scheduled', 'Agendado'),
        ('Live', 'Ao Vivo'),
        ('Final', 'Finalizado'),
        ('Postponed', 'Adiado'),
        ('Cancelled', 'Cancelado'),
    ]

    game_id = models.CharField(max_length=50, unique=True)
    date = models.DateTimeField()
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_games')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_games')
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=GAME_STATUS_CHOICES, default='Scheduled')
    season = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} - {self.date.strftime('%d/%m/%Y')}"

    class Meta:
        ordering = ['-date']

class PlayerGameStats(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='game_stats')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='player_stats')
    minutes = models.IntegerField()
    points = models.IntegerField()
    rebounds = models.IntegerField()
    assists = models.IntegerField()
    steals = models.IntegerField()
    blocks = models.IntegerField()
    turnovers = models.IntegerField()
    field_goals_made = models.IntegerField()
    field_goals_attempted = models.IntegerField()
    three_pointers_made = models.IntegerField()
    three_pointers_attempted = models.IntegerField()
    free_throws_made = models.IntegerField()
    free_throws_attempted = models.IntegerField()

    def __str__(self):
        return f"{self.player} - {self.game}"

    class Meta:
        ordering = ['-game__date']
        unique_together = ('player', 'game')

class BetSuggestion(models.Model):
    CONFIDENCE_CHOICES = [
        ('high', 'Alta'),
        ('medium', 'Média'),
        ('low', 'Baixa'),
    ]
    
    SUGGESTION_CHOICES = [
        ('over', 'Over'),
        ('under', 'Under'),
    ]
    
    MARKET_CHOICES = [
        ('points', 'Pontos'),
        ('assists', 'Assistências'),
        ('rebounds', 'Rebotes'),
        ('points_rebounds_assists', 'Pontos + Rebotes + Assistências'),
    ]
    
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='bet_suggestions')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='bet_suggestions')
    market = models.CharField(max_length=50, choices=MARKET_CHOICES)
    line = models.FloatField()
    suggestion = models.CharField(max_length=10, choices=SUGGESTION_CHOICES)
    confidence = models.CharField(max_length=10, choices=CONFIDENCE_CHOICES)
    reason = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    result = models.FloatField(null=True, blank=True)
    odds = models.FloatField(null=True, blank=True)
    hit = models.BooleanField(null=True, blank=True)
    
    class Meta:
        ordering = ['-confidence', 'game__date', 'player__last_name']
        
    def __str__(self):
        return f"{self.player} - {self.get_market_display()} {self.line} {self.suggestion.upper()}"
    
    def update_result(self, stats):
        """Atualiza o resultado da aposta baseado nas estatísticas do jogo"""
        if not stats:
            return
            
        if self.market == 'points':
            self.result = stats.points
        elif self.market == 'assists':
            self.result = stats.assists
        elif self.market == 'rebounds':
            self.result = stats.rebounds
        elif self.market == 'points_rebounds_assists':
            self.result = stats.points + stats.rebounds + stats.assists
            
        if self.result is not None:
            self.hit = (self.result > self.line) if self.suggestion == 'over' else (self.result < self.line)
            self.save()

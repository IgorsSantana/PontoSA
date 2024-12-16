from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from nba_api.stats.static import teams, players
from nba_api.stats.endpoints import leaguegamefinder, boxscoretraditionalv2, commonteamroster, scoreboard
from core.models import Team, Player, Game, PlayerGameStats
from datetime import datetime, timedelta
import time

class Command(BaseCommand):
    help = 'Importa dados da NBA API'

    def handle(self, *args, **options):
        self.stdout.write('Importando times...')
        self.import_teams()
        
        self.stdout.write('Importando jogadores...')
        self.import_players()
        
        self.stdout.write('Importando jogos recentes...')
        self.import_games()
        
        self.stdout.write(self.style.SUCCESS('Importação concluída com sucesso!'))

    def import_teams(self):
        nba_teams = teams.get_teams()
        for team_data in nba_teams:
            try:
                Team.objects.get_or_create(
                    team_id=team_data['id'],
                    defaults={
                        'name': team_data['nickname'],
                        'abbreviation': team_data['abbreviation'],
                        'city': team_data['city'],
                        'conference': team_data.get('confName', 'Unknown'),
                        'division': team_data.get('divName', 'Unknown')
                    }
                )
                self.stdout.write(f"Time importado: {team_data['full_name']}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Erro ao importar time: {str(e)}'))

    def import_players(self):
        # Primeiro, obtém todos os times
        all_teams = Team.objects.all()
        
        for team in all_teams:
            try:
                # Obtém o roster atual do time
                roster = commonteamroster.CommonTeamRoster(team_id=team.team_id)
                roster_data = roster.get_normalized_dict()
                
                # Processa cada jogador do roster
                for player_data in roster_data['CommonTeamRoster']:
                    try:
                        Player.objects.get_or_create(
                            player_id=player_data['PLAYER_ID'],
                            defaults={
                                'first_name': player_data['PLAYER'].split()[0],
                                'last_name': ' '.join(player_data['PLAYER'].split()[1:]),
                                'team': team,
                                'position': player_data.get('POSITION', 'N/A'),
                                'height': player_data.get('HEIGHT', ''),
                                'weight': player_data.get('WEIGHT', ''),
                                'birth_date': None  # A API não fornece data de nascimento no roster
                            }
                        )
                        self.stdout.write(f"Jogador importado: {player_data['PLAYER']}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Erro ao importar jogador: {str(e)}'))
                
                time.sleep(1)  # Respeita o rate limit da API
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Erro ao importar roster do time {team.name}: {str(e)}'))

    def import_games(self):
        try:
            # Obtém os jogos do dia atual e dos últimos 7 dias
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            for single_date in (start_date + timedelta(n) for n in range(8)):
                try:
                    # Obtém o scoreboard para o dia
                    date_str = single_date.strftime('%Y-%m-%d')
                    board = scoreboard.Scoreboard(game_date=date_str)
                    games_dict = board.get_normalized_dict()
                    
                    if 'GameHeader' not in games_dict:
                        continue
                    
                    for game_header in games_dict['GameHeader']:
                        try:
                            game_id = game_header['GAME_ID']
                            
                            # Evita duplicatas
                            if Game.objects.filter(game_id=game_id).exists():
                                continue
                            
                            # Obtém os times
                            home_team = Team.objects.get(team_id=game_header['HOME_TEAM_ID'])
                            away_team = Team.objects.get(team_id=game_header['VISITOR_TEAM_ID'])
                            
                            # Cria o jogo
                            game = Game.objects.create(
                                game_id=game_id,
                                date=parse_date(game_header['GAME_DATE_EST']),
                                home_team=home_team,
                                away_team=away_team,
                                home_score=game_header['HOME_TEAM_SCORE'],
                                away_score=game_header['VISITOR_TEAM_SCORE'],
                                season=game_header['SEASON'],
                                status=game_header['GAME_STATUS_TEXT']
                            )
                            
                            # Se o jogo já terminou, importa as estatísticas
                            if game_header['GAME_STATUS_TEXT'] == 'Final':
                                time.sleep(1)  # Respeita o rate limit da API
                                boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
                                box_dict = boxscore.get_normalized_dict()
                                
                                # Importa estatísticas dos jogadores
                                for stat in box_dict['PlayerStats']:
                                    try:
                                        player = Player.objects.get(player_id=stat['PLAYER_ID'])
                                        team = Team.objects.get(team_id=stat['TEAM_ID'])
                                        
                                        PlayerGameStats.objects.create(
                                            player=player,
                                            game=game,
                                            team=team,
                                            minutes=stat['MIN'],
                                            points=stat['PTS'],
                                            rebounds=stat['REB'],
                                            assists=stat['AST'],
                                            steals=stat['STL'],
                                            blocks=stat['BLK'],
                                            turnovers=stat['TO'],
                                            field_goals_made=stat['FGM'],
                                            field_goals_attempted=stat['FGA'],
                                            three_pointers_made=stat['FG3M'],
                                            three_pointers_attempted=stat['FG3A'],
                                            free_throws_made=stat['FTM'],
                                            free_throws_attempted=stat['FTA']
                                        )
                                    except Exception as e:
                                        self.stdout.write(self.style.WARNING(f'Erro ao importar estatísticas do jogador: {str(e)}'))
                            
                            self.stdout.write(f'Jogo importado: {home_team} vs {away_team} - {date_str}')
                            
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'Erro ao importar jogo: {str(e)}'))
                    
                    time.sleep(1)  # Respeita o rate limit da API
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Erro ao processar data {date_str}: {str(e)}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro ao importar jogos: {str(e)}'))
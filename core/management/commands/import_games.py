from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from nba_api.stats.endpoints import scoreboard, boxscoretraditionalv2
from core.models import Team, Player, Game, PlayerGameStats
from datetime import datetime, timedelta
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random
import json

class Command(BaseCommand):
    help = 'Importa jogos recentes da NBA'

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
    ]

    HEADERS = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Host': 'stats.nba.com',
        'Origin': 'https://www.nba.com',
        'Referer': 'https://www.nba.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true',
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Número de dias anteriores para importar (padrão: 7)'
        )
        parser.add_argument(
            '--retry',
            type=int,
            default=3,
            help='Número de tentativas para cada requisição (padrão: 3)'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=2,
            help='Tempo de espera entre requisições em segundos (padrão: 2)'
        )
        parser.add_argument(
            '--max-delay',
            type=int,
            default=10,
            help='Tempo máximo de espera entre tentativas em segundos (padrão: 10)'
        )

    def get_random_headers(self):
        headers = self.HEADERS.copy()
        headers['User-Agent'] = random.choice(self.USER_AGENTS)
        return headers

    def setup_session(self, retries=3):
        session = requests.Session()
        retry_strategy = Retry(
            total=retries,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
            respect_retry_after_header=True
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update(self.get_random_headers())
        return session

    def validate_response(self, response, context=""):
        """Valida e loga detalhes da resposta da API"""
        self.stdout.write(f"\nValidando resposta {context}:")
        self.stdout.write(f"Status Code: {response.status_code}")
        self.stdout.write(f"Content Type: {response.headers.get('content-type', 'não especificado')}")
        self.stdout.write(f"Tamanho da resposta: {len(response.content)} bytes")
        
        if response.status_code != 200:
            raise Exception(f"Status code inválido: {response.status_code}")
        
        if not response.content:
            raise Exception("Resposta vazia")
        
        try:
            return response.json()
        except json.JSONDecodeError as e:
            self.stdout.write("Conteúdo da resposta:")
            self.stdout.write(response.text[:500] + "..." if len(response.text) > 500 else response.text)
            raise Exception(f"Erro ao decodificar JSON: {str(e)}")

    def get_scoreboard_with_retry(self, date_str, retries=3, delay=2, max_delay=10):
        session = self.setup_session(retries)
        
        for attempt in range(retries):
            try:
                if attempt > 0:
                    wait_time = min(delay * (2 ** attempt), max_delay)
                    self.stdout.write(f"Tentativa {attempt + 1} de {retries} para {date_str} (aguardando {wait_time}s)")
                    time.sleep(wait_time)
                
                # Atualiza os headers a cada tentativa
                session.headers.update(self.get_random_headers())
                
                # Faz a requisição diretamente usando requests
                url = f"https://stats.nba.com/stats/scoreboardv3"
                params = {
                    'GameDate': date_str,
                    'LeagueID': '00',
                    'DayOffset': '0'
                }
                
                response = session.get(url, params=params, timeout=60)
                data = self.validate_response(response, f"scoreboard {date_str}")
                
                # Converte para o formato esperado
                if 'scoreboard' in data:
                    games = data['scoreboard'].get('games', [])
                    return {
                        'GameHeader': [{
                            'GAME_ID': game['gameId'],
                            'GAME_DATE_EST': game['gameEt'][:10],  # Usando gameEt e pegando só a data
                            'HOME_TEAM_ID': str(game['homeTeam']['teamId']),
                            'VISITOR_TEAM_ID': str(game['awayTeam']['teamId']),
                            'HOME_TEAM_SCORE': int(game['homeTeam'].get('score', 0)),
                            'VISITOR_TEAM_SCORE': int(game['awayTeam'].get('score', 0)),
                            'SEASON': str(datetime.now().year),  # Usando o ano atual como temporada
                            'GAME_STATUS_TEXT': game['gameStatusText']
                        } for game in games]
                    }
                else:
                    raise Exception("Formato de resposta inválido")
                
            except Exception as e:
                if attempt == retries - 1:  # Última tentativa
                    raise e
                self.stdout.write(self.style.WARNING(f"Erro na tentativa {attempt + 1}: {str(e)}"))
                
                # Espera adicional em caso de erro de rate limit
                if "429" in str(e):
                    time.sleep(max_delay)
        
        return None

    def get_boxscore_with_retry(self, game_id, retries=3, delay=2, max_delay=10):
        session = self.setup_session(retries)
        
        for attempt in range(retries):
            try:
                if attempt > 0:
                    wait_time = min(delay * (2 ** attempt), max_delay)
                    self.stdout.write(f"Tentativa {attempt + 1} de {retries} para boxscore {game_id} (aguardando {wait_time}s)")
                    time.sleep(wait_time)
                
                # Atualiza os headers a cada tentativa
                session.headers.update(self.get_random_headers())
                
                # Faz a requisição diretamente usando requests
                url = f"https://stats.nba.com/stats/boxscoretraditionalv3"
                params = {
                    'GameID': game_id,
                    'LeagueID': '00',
                    'EndPeriod': '0',
                    'EndRange': '0',
                    'RangeType': '0',
                    'StartPeriod': '0',
                    'StartRange': '0'
                }
                
                response = session.get(url, params=params, timeout=60)
                data = self.validate_response(response, f"boxscore {game_id}")
                
                # Debug da resposta
                self.stdout.write("\nEstrutura do boxscore:")
                self.stdout.write(json.dumps(data, indent=2)[:500] + "...")
                
                # Converte para o formato esperado
                if 'boxScoreTraditional' in data:
                    player_stats = []
                    
                    # Processa time da casa
                    home_team = data['boxScoreTraditional']['homeTeam']
                    home_team_id = str(home_team['teamId'])
                    for player in home_team.get('players', []):
                        stats = player.get('statistics', {})
                        player_stats.append({
                            'PLAYER_ID': str(player['personId']),
                            'TEAM_ID': home_team_id,
                            'MIN': stats.get('minutes', '0'),
                            'PTS': int(stats.get('points', 0)),
                            'REB': int(stats.get('reboundsTotal', 0)),
                            'AST': int(stats.get('assists', 0)),
                            'STL': int(stats.get('steals', 0)),
                            'BLK': int(stats.get('blocks', 0)),
                            'TO': int(stats.get('turnovers', 0)),
                            'FGM': int(stats.get('fieldGoalsMade', 0)),
                            'FGA': int(stats.get('fieldGoalsAttempted', 0)),
                            'FG3M': int(stats.get('threePointersMade', 0)),
                            'FG3A': int(stats.get('threePointersAttempted', 0)),
                            'FTM': int(stats.get('freeThrowsMade', 0)),
                            'FTA': int(stats.get('freeThrowsAttempted', 0))
                        })
                    
                    # Processa time visitante
                    away_team = data['boxScoreTraditional']['awayTeam']
                    away_team_id = str(away_team['teamId'])
                    for player in away_team.get('players', []):
                        stats = player.get('statistics', {})
                        player_stats.append({
                            'PLAYER_ID': str(player['personId']),
                            'TEAM_ID': away_team_id,
                            'MIN': stats.get('minutes', '0'),
                            'PTS': int(stats.get('points', 0)),
                            'REB': int(stats.get('reboundsTotal', 0)),
                            'AST': int(stats.get('assists', 0)),
                            'STL': int(stats.get('steals', 0)),
                            'BLK': int(stats.get('blocks', 0)),
                            'TO': int(stats.get('turnovers', 0)),
                            'FGM': int(stats.get('fieldGoalsMade', 0)),
                            'FGA': int(stats.get('fieldGoalsAttempted', 0)),
                            'FG3M': int(stats.get('threePointersMade', 0)),
                            'FG3A': int(stats.get('threePointersAttempted', 0)),
                            'FTM': int(stats.get('freeThrowsMade', 0)),
                            'FTA': int(stats.get('freeThrowsAttempted', 0))
                        })
                    
                    return {'PlayerStats': player_stats}
                else:
                    raise Exception("Formato de resposta inválido")
                
            except Exception as e:
                if attempt == retries - 1:  # Última tentativa
                    raise e
                self.stdout.write(self.style.WARNING(f"Erro na tentativa {attempt + 1}: {str(e)}"))
                
                # Espera adicional em caso de erro de rate limit
                if "429" in str(e):
                    time.sleep(max_delay)
        
        return None

    def handle(self, *args, **options):
        days = options['days']
        retries = options['retry']
        delay = options['delay']
        max_delay = options['max_delay']
        
        self.stdout.write(f'Iniciando importação dos jogos dos últimos {days} dias...')
        self.stdout.write(f'Configuração: {retries} tentativas por requisição, {delay}-{max_delay}s de espera entre requisições')
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            total_games = 0
            imported_games = 0
            skipped_games = 0
            missing_players = set()  # Para rastrear jogadores não encontrados
            
            for single_date in (start_date + timedelta(n) for n in range(days + 1)):
                try:
                    date_str = single_date.strftime('%Y-%m-%d')
                    self.stdout.write(f"\nBuscando jogos do dia: {date_str}")
                    
                    # Obtém o scoreboard do dia com retentativas
                    games_dict = self.get_scoreboard_with_retry(date_str, retries, delay, max_delay)
                    
                    if not games_dict or 'GameHeader' not in games_dict:
                        self.stdout.write(f"Nenhum jogo encontrado para {date_str}")
                        continue
                    
                    games = games_dict['GameHeader']
                    total_games += len(games)
                    
                    for game_header in games:
                        try:
                            game_id = game_header['GAME_ID']
                            
                            # Verifica se o jogo já existe
                            if Game.objects.filter(game_id=game_id).exists():
                                self.stdout.write(f"Jogo {game_id} já existe no banco de dados")
                                skipped_games += 1
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
                                time.sleep(delay)  # Respeita o rate limit da API
                                
                                try:
                                    # Obtém o boxscore com retentativas
                                    box_dict = self.get_boxscore_with_retry(game_id, retries, delay, max_delay)
                                    
                                    if box_dict and 'PlayerStats' in box_dict:
                                        # Importa estatísticas dos jogadores
                                        stats_imported = 0
                                        for stat in box_dict['PlayerStats']:
                                            try:
                                                player_id = stat['PLAYER_ID']
                                                try:
                                                    player = Player.objects.get(player_id=player_id)
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
                                                    stats_imported += 1
                                                except Player.DoesNotExist:
                                                    missing_players.add(player_id)
                                                    self.stdout.write(
                                                        self.style.WARNING(f'Jogador não encontrado: ID {player_id}')
                                                    )
                                                
                                            except Exception as e:
                                                self.stdout.write(
                                                    self.style.WARNING(f'Erro ao importar estatísticas do jogador: {str(e)}')
                                                )
                                        
                                        self.stdout.write(f"Estatísticas importadas: {stats_imported} jogadores")
                                    
                                except Exception as e:
                                    self.stdout.write(
                                        self.style.ERROR(f'Erro ao importar boxscore do jogo {game_id}: {str(e)}')
                                    )
                            
                            self.stdout.write(f'Jogo importado: {home_team} vs {away_team} - {date_str}')
                            imported_games += 1
                            
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Erro ao importar jogo: {str(e)}')
                            )
                    
                    # Espera aleatória entre requisições para evitar padrões
                    wait_time = random.uniform(delay, max_delay)
                    time.sleep(wait_time)
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Erro ao processar data {date_str}: {str(e)}')
                    )
            
            # Relatório final
            self.stdout.write(
                self.style.SUCCESS(f'\nImportação concluída!')
            )
            self.stdout.write(f'Total de jogos encontrados: {total_games}')
            self.stdout.write(f'Jogos importados com sucesso: {imported_games}')
            self.stdout.write(f'Jogos já existentes (pulados): {skipped_games}')
            if missing_players:
                self.stdout.write('\nJogadores não encontrados no banco:')
                for player_id in sorted(missing_players):
                    self.stdout.write(f'- ID {player_id}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erro ao importar jogos: {str(e)}')
            ) 
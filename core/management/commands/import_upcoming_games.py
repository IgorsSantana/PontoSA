from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Team, Game
import requests
from datetime import datetime, timedelta
import time
import logging
from dateutil.parser import parse
from django.utils.timezone import make_aware

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Importa os próximos jogos da NBA'

    def handle(self, *args, **options):
        # Configura o cabeçalho da requisição
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Data atual e data limite (7 dias à frente)
        today = timezone.now().date()
        end_date = today + timedelta(days=7)

        # URL base da API da NBA
        base_url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"

        try:
            # Faz a requisição para a API
            response = requests.get(base_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            games_added = 0
            games_updated = 0

            # Processa os jogos
            for game_data in data.get('leagueSchedule', {}).get('gameDates', []):
                try:
                    # Converte a data do jogo
                    game_date_str = game_data.get('gameDate')
                    self.stdout.write(f"Processando data: {game_date_str}")
                    
                    # Remove o horário da string de data
                    if ' ' in game_date_str:
                        game_date_str = game_date_str.split(' ')[0]
                    
                    try:
                        game_date = datetime.strptime(game_date_str, '%m/%d/%Y').date()
                    except ValueError:
                        try:
                            game_date = datetime.strptime(game_date_str, '%Y-%m-%d').date()
                        except ValueError:
                            self.stdout.write(self.style.WARNING(f"Formato de data inválido: {game_date_str}"))
                            continue
                    
                    # Verifica se a data está no intervalo desejado
                    if today <= game_date <= end_date:
                        for game in game_data.get('games', []):
                            try:
                                game_id = game.get('gameId')
                                self.stdout.write(f"Processando jogo ID: {game_id}")
                                
                                # Obtém os times
                                try:
                                    home_team = Team.objects.get(team_id=str(game['homeTeam']['teamId']))
                                    away_team = Team.objects.get(team_id=str(game['awayTeam']['teamId']))
                                except Team.DoesNotExist:
                                    self.stdout.write(self.style.WARNING(f"Time não encontrado para o jogo {game_id}"))
                                    continue
                                except KeyError as e:
                                    self.stdout.write(self.style.WARNING(f"Dados do time ausentes para o jogo {game_id}: {str(e)}"))
                                    continue

                                # Converte o horário do jogo
                                try:
                                    game_time_str = game.get('gameDateTimeEst', '')
                                    self.stdout.write(f"Horário do jogo: {game_time_str}")
                                    
                                    if game_time_str:
                                        # Converte a string ISO para datetime e torna aware
                                        game_time = make_aware(parse(game_time_str))
                                    else:
                                        # Se não tiver horário específico, usa meia-noite
                                        game_time = make_aware(datetime.combine(game_date, datetime.min.time()))
                                except (ValueError, TypeError) as e:
                                    self.stdout.write(self.style.WARNING(f"Erro ao converter horário do jogo {game_id}: {str(e)}"))
                                    game_time = make_aware(datetime.combine(game_date, datetime.min.time()))

                                # Cria ou atualiza o jogo
                                game_obj, created = Game.objects.update_or_create(
                                    game_id=game_id,
                                    defaults={
                                        'date': game_time,
                                        'home_team': home_team,
                                        'away_team': away_team,
                                        'status': 'Scheduled',
                                        'season': '2023-24',  # Temporada atual
                                    }
                                )

                                if created:
                                    games_added += 1
                                    self.stdout.write(self.style.SUCCESS(f"Jogo adicionado: {home_team} vs {away_team}"))
                                else:
                                    games_updated += 1
                                    self.stdout.write(self.style.SUCCESS(f"Jogo atualizado: {home_team} vs {away_team}"))

                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f"Erro ao processar jogo individual: {str(e)}"))
                                continue

                            # Pequena pausa para não sobrecarregar a API
                            time.sleep(0.1)

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Erro ao processar data: {str(e)}"))
                    continue

            self.stdout.write(
                self.style.SUCCESS(
                    f'Importação concluída! {games_added} jogos adicionados, {games_updated} jogos atualizados.'
                )
            )

        except requests.exceptions.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f'Erro ao acessar a API da NBA: {str(e)}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erro inesperado: {str(e)}')
            ) 
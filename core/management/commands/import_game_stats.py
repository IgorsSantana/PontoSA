from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import Game, Player, PlayerGameStats
import requests
import json
import time

class Command(BaseCommand):
    help = 'Importa estatísticas dos jogos finalizados'

    def handle(self, *args, **options):
        # Obtém jogos dos últimos 30 dias
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        games = Game.objects.filter(
            date__range=[start_date, end_date],
            status='Final'
        ).order_by('-date')
        
        self.stdout.write(f"Encontrados {games.count()} jogos finalizados")
        
        stats_added = 0
        stats_updated = 0
        
        for game in games:
            try:
                self.stdout.write(f"\nProcessando jogo: {game}")
                
                # URL da API da NBA para estatísticas do jogo
                url = f"https://stats.nba.com/stats/boxscoretraditionalv2"
                params = {
                    'GameID': game.game_id,
                    'StartPeriod': 0,
                    'EndPeriod': 10,
                    'StartRange': 0,
                    'EndRange': 28800,
                    'RangeType': 2
                }
                headers = {
                    'Host': 'stats.nba.com',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'x-nba-stats-origin': 'stats',
                    'x-nba-stats-token': 'true',
                    'Connection': 'keep-alive',
                    'Referer': 'https://stats.nba.com/',
                    'Pragma': 'no-cache',
                    'Cache-Control': 'no-cache',
                    'Sec-Fetch-Site': 'same-origin',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Dest': 'empty'
                }
                
                max_retries = 3
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        response = requests.get(url, params=params, headers=headers, timeout=30)
                        
                        if response.status_code == 429:  # Rate limit
                            retry_count += 1
                            self.stdout.write(self.style.WARNING(f"Rate limit atingido, tentativa {retry_count} de {max_retries}"))
                            time.sleep(60)  # Espera 1 minuto
                            continue
                            
                        response.raise_for_status()
                        data = response.json()
                        break
                        
                    except requests.exceptions.RequestException as e:
                        retry_count += 1
                        if retry_count == max_retries:
                            raise Exception(f"Erro após {max_retries} tentativas: {str(e)}")
                        self.stdout.write(self.style.WARNING(f"Erro na requisição, tentativa {retry_count} de {max_retries}"))
                        time.sleep(5)
                        continue
                
                # Processa os dados dos jogadores
                player_stats = data['resultSets'][0]['rowSet']
                
                for row in player_stats:
                    try:
                        player_id = row[4]
                        player = Player.objects.get(player_id=player_id)
                        
                        # Converte minutos para inteiro
                        minutes_str = row[8]
                        if ':' in minutes_str:
                            minutes, seconds = minutes_str.split(':')
                            minutes = int(minutes) + (int(seconds) / 60)
                        else:
                            minutes = float(minutes_str)
                        minutes = int(round(minutes))
                        
                        stats, created = PlayerGameStats.objects.update_or_create(
                            player=player,
                            game=game,
                            defaults={
                                'minutes': minutes,
                                'points': int(row[26]),
                                'rebounds': int(row[20]),
                                'assists': int(row[21]),
                                'steals': int(row[22]),
                                'blocks': int(row[23]),
                                'turnovers': int(row[24]),
                                'field_goals_made': int(row[9]),
                                'field_goals_attempted': int(row[10]),
                                'three_pointers_made': int(row[12]),
                                'three_pointers_attempted': int(row[13]),
                                'free_throws_made': int(row[15]),
                                'free_throws_attempted': int(row[16])
                            }
                        )
                        
                        if created:
                            stats_added += 1
                            self.stdout.write(f"Estatísticas adicionadas para {player}")
                        else:
                            stats_updated += 1
                            self.stdout.write(f"Estatísticas atualizadas para {player}")
                            
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Erro ao processar jogador: {str(e)}"))
                        continue
                
                # Espera 2 segundos entre cada jogo para evitar rate limit
                time.sleep(2)
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao processar jogo {game.game_id}: {str(e)}"))
                continue
                
        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída! {stats_added} estatísticas adicionadas, {stats_updated} atualizadas."
        )) 
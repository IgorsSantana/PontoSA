from django.core.management.base import BaseCommand
from nba_api.stats.endpoints import commonteamroster
from core.models import Team, Player
import time

class Command(BaseCommand):
    help = 'Importa jogadores ativos da NBA'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando importação dos jogadores...')
        
        try:
            # Obtém todos os times
            teams = Team.objects.all()
            total_players = 0
            imported_players = 0
            
            for team in teams:
                try:
                    self.stdout.write(f"\nBuscando jogadores do time: {team.city} {team.name}")
                    
                    # Obtém o roster atual do time
                    roster = commonteamroster.CommonTeamRoster(team_id=team.team_id)
                    roster_data = roster.get_normalized_dict()
                    
                    # Processa cada jogador do roster
                    players_data = roster_data.get('CommonTeamRoster', [])
                    total_players += len(players_data)
                    
                    for player_data in players_data:
                        try:
                            # Gera a URL da foto do jogador
                            photo_url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_data['PLAYER_ID']}.png"
                            
                            player, created = Player.objects.get_or_create(
                                player_id=player_data['PLAYER_ID'],
                                defaults={
                                    'first_name': player_data['PLAYER'].split()[0],
                                    'last_name': ' '.join(player_data['PLAYER'].split()[1:]),
                                    'team': team,
                                    'position': player_data.get('POSITION', 'N/A'),
                                    'height': player_data.get('HEIGHT', ''),
                                    'weight': player_data.get('WEIGHT', ''),
                                    'birth_date': None,
                                    'photo_url': photo_url
                                }
                            )
                            
                            # Se o jogador já existe, atualiza o time e a foto
                            if not created:
                                player.team = team
                                player.photo_url = photo_url
                                player.save()
                            
                            action = "criado" if created else "atualizado"
                            self.stdout.write(f"Jogador {action}: {player_data['PLAYER']}")
                            imported_players += 1
                            
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Erro ao importar jogador {player_data.get("PLAYER")}: {str(e)}')
                            )
                    
                    # Respeita o rate limit da API
                    time.sleep(1)
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Erro ao importar roster do time {team.name}: {str(e)}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'\nImportação concluída! {imported_players}/{total_players} jogadores importados.')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erro ao importar jogadores: {str(e)}')
            ) 
from django.core.management.base import BaseCommand
from nba_api.stats.static import teams
from core.models import Team

class Command(BaseCommand):
    help = 'Importa times da NBA'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando importação dos times...')
        
        try:
            nba_teams = teams.get_teams()
            total_teams = len(nba_teams)
            imported = 0
            
            for team_data in nba_teams:
                try:
                    logo_url = f"https://cdn.nba.com/logos/nba/{team_data['id']}/global/L/logo.svg"
                    
                    team, created = Team.objects.get_or_create(
                        team_id=team_data['id'],
                        defaults={
                            'name': team_data['nickname'],
                            'abbreviation': team_data['abbreviation'],
                            'city': team_data['city'],
                            'conference': team_data.get('confName', 'Unknown'),
                            'division': team_data.get('divName', 'Unknown'),
                            'logo_url': logo_url
                        }
                    )
                    
                    if not created:
                        team.logo_url = logo_url
                        team.save()
                    
                    action = "criado" if created else "atualizado"
                    self.stdout.write(f"Time {action}: {team_data['full_name']}")
                    imported += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Erro ao importar time {team_data.get("full_name")}: {str(e)}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'Importação concluída! {imported}/{total_teams} times importados.')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erro ao buscar times da API: {str(e)}')
            ) 
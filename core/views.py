from django.shortcuts import render, redirect
from django.db.models import Q, Avg, Count, StdDev, F, FloatField, Value, Sum
from django.db.models.functions import Cast
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Game, Player, Team, PlayerGameStats, BetSuggestion
import random

def index(request):
    # Obtém os jogos dos últimos 7 dias
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    recent_games = Game.objects.filter(
        date__range=[start_date, end_date]
    ).order_by('-date')
    
    # Estatísticas dos jogadores
    top_scorers = PlayerGameStats.objects.values(
        'player__first_name', 'player__last_name', 'player__team__name'
    ).annotate(
        avg_points=Avg('points'),
        games_played=Count('game', distinct=True)
    ).filter(games_played__gte=3).order_by('-avg_points')[:5]
    
    top_assists = PlayerGameStats.objects.values(
        'player__first_name', 'player__last_name', 'player__team__name'
    ).annotate(
        avg_assists=Avg('assists'),
        games_played=Count('game', distinct=True)
    ).filter(games_played__gte=3).order_by('-avg_assists')[:5]
    
    context = {
        'recent_games': recent_games,
        'top_scorers': top_scorers,
        'top_assists': top_assists,
    }
    
    return render(request, 'core/index.html', context)

def games(request):
    # Filtra jogos por data
    date_str = request.GET.get('date')
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date = timezone.now().date()
    else:
        date = timezone.now().date()
    
    # Converte a data para datetime com timezone
    start_datetime = timezone.make_aware(datetime.combine(date, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(date, datetime.max.time()))
    
    # Filtra os jogos usando range de datetime
    games = Game.objects.filter(
        date__range=(start_datetime, end_datetime)
    ).select_related('home_team', 'away_team').order_by('date')
    
    context = {
        'games': games,
        'selected_date': date.strftime('%Y-%m-%d'),
    }
    
    return render(request, 'core/games.html', context)

def game_detail(request, game_id):
    game = Game.objects.get(game_id=game_id)
    
    # Busca jogadores do time da casa
    home_players = Player.objects.filter(
        team=game.home_team
    ).annotate(
        avg_points=Avg('game_stats__points'),
        avg_assists=Avg('game_stats__assists'),
        avg_rebounds=Avg('game_stats__rebounds'),
        avg_minutes=Avg('game_stats__minutes'),
        avg_steals=Avg('game_stats__steals'),
        avg_blocks=Avg('game_stats__blocks'),
        games_played=Count('game_stats')
    ).order_by('-avg_points')
    
    # Busca jogadores do time visitante
    away_players = Player.objects.filter(
        team=game.away_team
    ).annotate(
        avg_points=Avg('game_stats__points'),
        avg_assists=Avg('game_stats__assists'),
        avg_rebounds=Avg('game_stats__rebounds'),
        avg_minutes=Avg('game_stats__minutes'),
        avg_steals=Avg('game_stats__steals'),
        avg_blocks=Avg('game_stats__blocks'),
        games_played=Count('game_stats')
    ).order_by('-avg_points')
    
    # Processa força dos jogadores
    for players in [home_players, away_players]:
        for player in players:
            if player.games_played >= 5:  # Mínimo de 5 jogos
                if player.avg_points >= 20:
                    player.strength = "Pontuador Elite"
                elif player.avg_assists >= 7:
                    player.strength = "Playmaker"
                elif player.avg_rebounds >= 10:
                    player.strength = "Reboteiro"
                elif player.avg_steals >= 1.5:
                    player.strength = "Defensor"
                elif player.avg_blocks >= 1.5:
                    player.strength = "Protetor do Aro"
                elif player.avg_points >= 15:
                    player.strength = "Pontuador"
                elif player.avg_assists >= 5:
                    player.strength = "Distribuidor"
                elif player.avg_rebounds >= 7:
                    player.strength = "Forte nos Rebotes"
    
    # Estatísticas do jogo se já tiver acontecido
    home_stats = None
    away_stats = None
    if game.status == 'Final':
        home_stats = PlayerGameStats.objects.filter(
            game=game,
            player__team=game.home_team
        ).select_related('player').order_by('-points')
        
        away_stats = PlayerGameStats.objects.filter(
            game=game,
            player__team=game.away_team
        ).select_related('player').order_by('-points')
    
    context = {
        'game': game,
        'home_players': home_players,
        'away_players': away_players,
        'home_stats': home_stats,
        'away_stats': away_stats,
    }
    
    return render(request, 'core/game_detail.html', context)

def players(request):
    # Busca jogadores
    search = request.GET.get('search', '')
    if search:
        players = Player.objects.filter(
            Q(first_name__icontains=search) | 
            Q(last_name__icontains=search) |
            Q(team__name__icontains=search)
        ).select_related('team')
    else:
        players = Player.objects.all().select_related('team')
    
    # Estatísticas médias completas
    player_stats = PlayerGameStats.objects.values(
        'player'
    ).annotate(
        # Estatísticas básicas
        avg_points=Avg('points'),
        avg_rebounds=Avg('rebounds'),
        avg_assists=Avg('assists'),
        avg_steals=Avg('steals'),
        avg_blocks=Avg('blocks'),
        avg_minutes=Avg('minutes'),
        
        # Arremessos
        avg_field_goals_made=Avg('field_goals_made'),
        avg_field_goals_attempted=Avg('field_goals_attempted'),
        avg_three_pointers_made=Avg('three_pointers_made'),
        avg_three_pointers_attempted=Avg('three_pointers_attempted'),
        avg_free_throws_made=Avg('free_throws_made'),
        avg_free_throws_attempted=Avg('free_throws_attempted'),
        
        # Contadores
        games_played=Count('game', distinct=True),
        total_points=Sum('points'),
        total_rebounds=Sum('rebounds'),
        total_assists=Sum('assists'),
        total_steals=Sum('steals'),
        total_blocks=Sum('blocks'),
        total_minutes=Sum('minutes')
    ).filter(
        # Filtra apenas jogadores com minutos significativos
        minutes__gte=10
    )
    
    # Combina informações dos jogadores com suas estatísticas
    players_with_stats = []
    for player in players:
        stats = next((s for s in player_stats if s['player'] == player.id), None)
        if stats:
            # Calcula porcentagens de arremesso
            if stats['avg_field_goals_attempted'] > 0:
                stats['field_goal_percentage'] = (
                    stats['avg_field_goals_made'] / stats['avg_field_goals_attempted'] * 100
                )
            else:
                stats['field_goal_percentage'] = 0
                
            if stats['avg_three_pointers_attempted'] > 0:
                stats['three_point_percentage'] = (
                    stats['avg_three_pointers_made'] / stats['avg_three_pointers_attempted'] * 100
                )
            else:
                stats['three_point_percentage'] = 0
                
            if stats['avg_free_throws_attempted'] > 0:
                stats['free_throw_percentage'] = (
                    stats['avg_free_throws_made'] / stats['avg_free_throws_attempted'] * 100
                )
            else:
                stats['free_throw_percentage'] = 0
            
            # Calcula força do jogador
            strength = None
            if stats['games_played'] >= 5:  # Mínimo de 5 jogos
                if stats['avg_points'] >= 20:
                    strength = "Pontuador Elite"
                elif stats['avg_assists'] >= 7:
                    strength = "Playmaker"
                elif stats['avg_rebounds'] >= 10:
                    strength = "Reboteiro"
                elif stats['avg_steals'] >= 1.5:
                    strength = "Defensor"
                elif stats['avg_blocks'] >= 1.5:
                    strength = "Protetor do Aro"
                elif stats['avg_points'] >= 15:
                    strength = "Pontuador"
                elif stats['avg_assists'] >= 5:
                    strength = "Distribuidor"
                elif stats['avg_rebounds'] >= 7:
                    strength = "Forte nos Rebotes"
            
            players_with_stats.append({
                'player': player,
                'stats': stats,
                'strength': strength
            })
    
    # Ordena por pontos médios
    players_with_stats.sort(key=lambda x: x['stats']['avg_points'] or 0, reverse=True)
    
    context = {
        'players': players_with_stats,
        'search': search,
    }
    
    return render(request, 'core/players.html', context)

def player_detail(request, player_id):
    player = Player.objects.get(player_id=player_id)
    
    # Últimos jogos do jogador
    recent_games = PlayerGameStats.objects.filter(
        player=player
    ).select_related('game', 'game__home_team', 'game__away_team').order_by('-game__date')[:10]
    
    # Estatísticas médias da temporada
    season_stats = PlayerGameStats.objects.filter(
        player=player
    ).aggregate(
        avg_points=Avg('points'),
        avg_rebounds=Avg('rebounds'),
        avg_assists=Avg('assists'),
        avg_steals=Avg('steals'),
        avg_blocks=Avg('blocks'),
        avg_minutes=Avg('minutes'),
        avg_field_goals_made=Avg('field_goals_made'),
        avg_field_goals_attempted=Avg('field_goals_attempted'),
        avg_three_pointers_made=Avg('three_pointers_made'),
        avg_three_pointers_attempted=Avg('three_pointers_attempted'),
        avg_free_throws_made=Avg('free_throws_made'),
        avg_free_throws_attempted=Avg('free_throws_attempted'),
        games_played=Count('game', distinct=True)
    )
    
    # Calcula porcentagens
    if season_stats['avg_field_goals_attempted'] > 0:
        season_stats['field_goal_percentage'] = (
            season_stats['avg_field_goals_made'] / season_stats['avg_field_goals_attempted'] * 100
        )
    else:
        season_stats['field_goal_percentage'] = 0
        
    if season_stats['avg_three_pointers_attempted'] > 0:
        season_stats['three_point_percentage'] = (
            season_stats['avg_three_pointers_made'] / season_stats['avg_three_pointers_attempted'] * 100
        )
    else:
        season_stats['three_point_percentage'] = 0
        
    if season_stats['avg_free_throws_attempted'] > 0:
        season_stats['free_throw_percentage'] = (
            season_stats['avg_free_throws_made'] / season_stats['avg_free_throws_attempted'] * 100
        )
    else:
        season_stats['free_throw_percentage'] = 0
    
    # Serializa os dados dos jogos para os gráficos
    games_data = []
    for game in recent_games:
        games_data.append({
            'game': {
                'date': game.game.date.isoformat(),
                'home_team': game.game.home_team.name,
                'away_team': game.game.away_team.name,
            },
            'points': game.points,
            'rebounds': game.rebounds,
            'assists': game.assists,
            'steals': game.steals,
            'blocks': game.blocks,
            'minutes': game.minutes,
            'field_goals_made': game.field_goals_made,
            'field_goals_attempted': game.field_goals_attempted,
            'three_pointers_made': game.three_pointers_made,
            'three_pointers_attempted': game.three_pointers_attempted,
            'free_throws_made': game.free_throws_made,
            'free_throws_attempted': game.free_throws_attempted,
        })
    
    # Calcula força do jogador
    strength = None
    if season_stats['games_played'] >= 5:  # Mínimo de 5 jogos
        if season_stats['avg_points'] >= 20:
            strength = "Pontuador Elite"
        elif season_stats['avg_assists'] >= 7:
            strength = "Playmaker"
        elif season_stats['avg_rebounds'] >= 10:
            strength = "Reboteiro"
        elif season_stats['avg_steals'] >= 1.5:
            strength = "Defensor"
        elif season_stats['avg_blocks'] >= 1.5:
            strength = "Protetor do Aro"
        elif season_stats['avg_points'] >= 15:
            strength = "Pontuador"
        elif season_stats['avg_assists'] >= 5:
            strength = "Distribuidor"
        elif season_stats['avg_rebounds'] >= 7:
            strength = "Forte nos Rebotes"
    
    context = {
        'player': player,
        'recent_games': recent_games,
        'season_stats': season_stats,
        'games_data': games_data,
        'strength': strength,
    }
    
    return render(request, 'core/player_detail.html', context)

def generate_bet_suggestions():
    """Função auxiliar para gerar sugestões de apostas"""
    try:
        print("Iniciando geração de sugestões...")
        # Limpa sugestões antigas
        BetSuggestion.objects.all().delete()
        
        # Obtém jogos dos próximos 7 dias que ainda não começaram
        today = timezone.now()
        end_date = today + timedelta(days=7)
        upcoming_games = Game.objects.filter(
            date__range=[today, end_date],
            status='Scheduled'
        ).order_by('date')
        
        print(f"Encontrados {upcoming_games.count()} jogos futuros")
        
        for game in upcoming_games:
            try:
                print(f"\nProcessando jogo: {game}")
                # Obtém os principais jogadores de cada time (top 5 por pontuação média)
                home_players = get_top_players(game.home_team)
                away_players = get_top_players(game.away_team)
                print(f"Jogadores do time da casa: {len(list(home_players))}")
                print(f"Jogadores visitantes: {len(list(away_players))}")
                
                all_players = list(home_players) + list(away_players)
                game_suggestions = []
                
                for player in all_players:
                    try:
                        print(f"\nAnalisando jogador: {player}")
                        # Obtém estatísticas dos últimos 10 jogos do jogador
                        recent_stats = PlayerGameStats.objects.filter(
                            player=player,
                            game__date__lt=today  # Apenas jogos passados
                        ).order_by('-game__date')[:10]
                        
                        print(f"Jogos recentes encontrados: {recent_stats.count()}")
                        
                        if recent_stats.count() >= 5:
                            stats = analyze_player_stats(recent_stats)
                            if not stats:
                                print("Sem estatísticas suficientes")
                                continue
                                
                            # Gera sugestões apenas para mercados principais
                            main_markets = [
                                ('points', 'Pontos'),
                                ('assists', 'Assistências'),
                                ('rebounds', 'Rebotes'),
                                ('points_rebounds_assists', 'Pontos + Rebotes + Assistências')
                            ]
                            
                            for market_key, market_name in main_markets:
                                try:
                                    suggestion = generate_market_suggestion(
                                        player, stats, market_key, market_name
                                    )
                                    if suggestion:
                                        print(f"Sugestão gerada para {market_name}")
                                        suggestion['odds'] = round(1.5 + random.random(), 2)
                                        game_suggestions.append(suggestion)
                                except Exception as e:
                                    print(f"Erro ao gerar sugestão para {player} no mercado {market_key}: {str(e)}")
                                    continue
                        else:
                            print("Jogos insuficientes")
                    except Exception as e:
                        print(f"Erro ao processar jogador {player}: {str(e)}")
                        continue
                
                print(f"\nSugestões geradas para o jogo: {len(game_suggestions)}")
                
                # Ordena sugestões do jogo por confiança e consistência
                game_suggestions.sort(key=lambda x: (
                    2 if x['confidence'] == 'high' else 1 if x['confidence'] == 'medium' else 0,
                    x['consistency']
                ), reverse=True)
                
                # Pega as 4 melhores sugestões do jogo
                for suggestion in game_suggestions[:4]:
                    try:
                        BetSuggestion.objects.create(
                            game=game,
                            player=suggestion['player'],
                            market=suggestion['market'],
                            line=suggestion['line'],
                            suggestion=suggestion['suggestion'],
                            confidence=suggestion['confidence'],
                            reason=suggestion['reason'],
                            odds=suggestion['odds']
                        )
                        print(f"Sugestão salva: {suggestion['player']} - {suggestion['market']}")
                    except Exception as e:
                        print(f"Erro ao salvar sugestão: {str(e)}")
                        continue
            except Exception as e:
                print(f"Erro ao processar jogo {game}: {str(e)}")
                continue
                
        print("\nGeração de sugestões concluída!")
        return True
    except Exception as e:
        print(f"Erro ao gerar sugestões: {str(e)}")
        raise

def get_top_players(team, limit=5):
    """Obtém os principais jogadores de um time baseado em média de pontos"""
    return Player.objects.filter(team=team).annotate(
        avg_points=Avg('game_stats__points'),
        games_played=Count('game_stats'),
        avg_minutes=Avg('game_stats__minutes')
    ).filter(
        games_played__gte=5,
        avg_minutes__gte=15
    ).order_by('-avg_points')[:limit]

def analyze_player_stats(recent_stats):
    """Analisa estatísticas recentes do jogador"""
    stats = {
        'points': {'values': []},
        'rebounds': {'values': []},
        'assists': {'values': []},
        'points_rebounds_assists': {'values': []},
    }
    
    # Coleta valores apenas de jogos onde o jogador teve minutos significativos
    for game in recent_stats:
        if game.minutes >= 15:  # Mínimo de 15 minutos jogados
            stats['points']['values'].append(game.points)
            stats['rebounds']['values'].append(game.rebounds)
            stats['assists']['values'].append(game.assists)
            stats['points_rebounds_assists']['values'].append(
                game.points + game.rebounds + game.assists
            )
    
    # Se não tiver jogos suficientes com minutos significativos, retorna None
    if not all(len(stat['values']) >= 5 for stat in stats.values()):
        return None
    
    # Calcula médias e desvio padrão
    for stat in stats:
        values = stats[stat]['values']
        avg = sum(values) / len(values)
        variance = sum((x - avg) ** 2 for x in values) / len(values)
        std = variance ** 0.5
        consistency = (1 - (std / avg if avg > 0 else 0)) * 100 if avg > 0 else 0
        
        stats[stat].update({
            'avg': avg,
            'std': std,
            'consistency': consistency,
            'min': min(values),
            'max': max(values)
        })
    
    return stats

def generate_market_suggestion(player, stats, market_key, market_name):
    """Gera sugestão para um mercado específico"""
    stat_data = stats[market_key]
    
    if stat_data['avg'] <= 0:
        return None
        
    # Calcula a linha sugerida (arredonda para .5 mais próximo)
    line = round(stat_data['avg'] * 2) / 2
    
    # Analisa a tendência dos últimos jogos
    values = stat_data['values']
    hits = sum(1 for v in values if v > line)
    trend = hits / len(values)
    
    # Determina a sugestão e confiança
    if trend > 0.6:  # Mais flexível com o trend para over
        suggestion = 'over'
        confidence = 'high' if trend > 0.7 and stat_data['consistency'] > 60 else 'medium'
    elif trend < 0.4:  # Mais flexível com o trend para under
        suggestion = 'under'
        confidence = 'high' if trend < 0.3 and stat_data['consistency'] > 60 else 'medium'
    else:
        return None
    
    # Ajusta a linha baseado na tendência
    if suggestion == 'over':
        line = min(values) + 0.5  # Linha mais conservadora para over
    else:
        line = max(values) - 0.5  # Linha mais conservadora para under
    
    reason = f"""
    Análise dos últimos {len(values)} jogos:
    - Média: {stat_data['avg']:.1f}
    - Desvio Padrão: {stat_data['std']:.1f}
    - Consistência: {stat_data['consistency']:.1f}%
    - Taxa de Over: {trend*100:.1f}%
    
    Jogos acima da linha ({line}): {hits}
    Jogos abaixo da linha: {len(values) - hits}
    """
    
    return {
        'player': player,
        'market': market_key,
        'line': line,
        'suggestion': suggestion,
        'confidence': confidence,
        'reason': reason.strip(),
        'consistency': stat_data['consistency']
    }

def bet_suggestions(request):
    """View para exibir sugestões de apostas"""
    try:
        # Verifica se precisa gerar novas sugestões
        generate = request.GET.get('generate', 'false').lower() == 'true'
        if generate:
            generate_bet_suggestions()
            # Redireciona para a página sem o parâmetro generate para evitar regeneração
            return redirect('bet_suggestions')
        
        # Obtém as sugestões existentes
        suggestions = BetSuggestion.objects.select_related(
            'game', 'player', 'player__team'
        ).order_by(
            'game__date', 'game', '-confidence'
        )
        
        # Agrupa sugestões por data e jogo
        grouped_suggestions = {}
        for suggestion in suggestions:
            game_date = suggestion.game.date.date()
            if game_date not in grouped_suggestions:
                grouped_suggestions[game_date] = {}
                
            if suggestion.game not in grouped_suggestions[game_date]:
                grouped_suggestions[game_date][suggestion.game] = []
                
            grouped_suggestions[game_date][suggestion.game].append(suggestion)
            
            # Atualiza o resultado se o jogo já terminou
            if suggestion.game.status == 'Final' and suggestion.result is None:
                stats = PlayerGameStats.objects.filter(
                    game=suggestion.game,
                    player=suggestion.player
                ).first()
                suggestion.update_result(stats)
        
        context = {
            'grouped_suggestions': grouped_suggestions,
        }
        
        return render(request, 'core/bet_suggestions.html', context)
        
    except Exception as e:
        print(f"Erro ao exibir sugestões: {str(e)}")
        # Em caso de erro, limpa as sugestões e mostra a página vazia
        BetSuggestion.objects.all().delete()
        return render(request, 'core/bet_suggestions.html', {'grouped_suggestions': {}})

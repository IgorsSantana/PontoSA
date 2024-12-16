from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('games/', views.games, name='games'),
    path('games/<str:game_id>/', views.game_detail, name='game_detail'),
    path('players/', views.players, name='players'),
    path('players/<str:player_id>/', views.player_detail, name='player_detail'),
    path('bet-suggestions/', views.bet_suggestions, name='bet_suggestions'),
] 
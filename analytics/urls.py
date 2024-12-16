from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('team/<int:team_id>/', views.TeamAnalytics.as_view(), name='team_analytics'),
    path('player/<int:player_id>/', views.PlayerAnalytics.as_view(), name='player_analytics'),
    path('prediction/<int:home_team_id>/<int:away_team_id>/', views.GamePrediction.as_view(), name='game_prediction'),
] 
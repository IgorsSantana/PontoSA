from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'teams', views.TeamViewSet)
router.register(r'players', views.PlayerViewSet)
router.register(r'games', views.GameViewSet)
router.register(r'player-stats', views.PlayerGameStatsViewSet)

app_name = 'api'

urlpatterns = [
    path('', include(router.urls)),
] 
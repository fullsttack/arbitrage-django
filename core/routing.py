from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/arbitrage/", consumers.ArbitrageConsumer.as_asgi()),
]


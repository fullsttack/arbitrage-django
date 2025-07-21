import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
import redis.asyncio as redis
from django.conf import settings

logger = logging.getLogger(__name__)

class ArbitrageConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis_client = None
        self.monitor_task = None

    async def connect(self):
        await self.channel_layer.group_add('arbitrage_updates', self.channel_name)
        await self.channel_layer.group_add('price_updates', self.channel_name)
        await self.accept()
        
        # Initialize Redis
        self.redis_client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            db=getattr(settings, 'REDIS_DB', 0),
            decode_responses=True
        )
        
        # Start Redis monitoring
        self.monitor_task = asyncio.create_task(self._monitor_redis())
        
        # Send initial data
        await self.send_initial_data()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('arbitrage_updates', self.channel_name)
        await self.channel_layer.group_discard('price_updates', self.channel_name)
        
        if self.monitor_task:
            self.monitor_task.cancel()
        
        if self.redis_client:
            await self.redis_client.close()

    async def _monitor_redis(self):
        """Monitor Redis stats and send updates every 2 seconds"""
        while True:
            try:
                # Get Redis info
                redis_info = await self.redis_client.info()
                
                # Get key counts
                price_keys = await self.redis_client.keys("prices:*")
                opportunity_keys = await self.redis_client.keys("opportunity:*")
                
                # Get memory usage
                memory_used = redis_info.get('used_memory_human', '0B')
                memory_peak = redis_info.get('used_memory_peak_human', '0B')
                
                # Get connection info
                connected_clients = redis_info.get('connected_clients', 0)
                total_commands = redis_info.get('total_commands_processed', 0)
                
                redis_stats = {
                    'connected_clients': connected_clients,
                    'total_commands': total_commands,
                    'memory_used': memory_used,
                    'memory_peak': memory_peak,
                    'price_keys_count': len(price_keys),
                    'opportunity_keys_count': len(opportunity_keys),
                    'uptime_seconds': redis_info.get('uptime_in_seconds', 0),
                    'version': redis_info.get('redis_version', 'Unknown'),
                    'keyspace_hits': redis_info.get('keyspace_hits', 0),
                    'keyspace_misses': redis_info.get('keyspace_misses', 0),
                }
                
                await self.send(text_data=json.dumps({
                    'type': 'redis_stats',
                    'data': redis_stats
                }))
                
            except Exception as e:
                logger.error(f"Error monitoring Redis: {e}")
                
            await asyncio.sleep(2)  # Update every 2 seconds

    async def send_initial_data(self):
        """Send initial opportunities and prices"""
        try:
            # Get recent opportunities
            opportunity_keys = await self.redis_client.keys("opportunity:*")
            opportunity_keys.sort(reverse=True)
            
            opportunities = []
            for key in opportunity_keys[:50]:  # Latest 50
                data = await self.redis_client.get(key)
                if data:
                    opportunities.append(json.loads(data))
            
            await self.send(text_data=json.dumps({
                'type': 'initial_opportunities',
                'data': opportunities
            }))
            
            # Get current prices
            price_keys = await self.redis_client.keys("prices:*")
            prices = []
            
            for key in price_keys:
                data = await self.redis_client.get(key)
                if data:
                    prices.append(json.loads(data))
            
            await self.send(text_data=json.dumps({
                'type': 'initial_prices',
                'data': prices
            }))
            
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")

    async def send_opportunities(self, event):
        """Send new arbitrage opportunities"""
        await self.send(text_data=json.dumps({
            'type': 'opportunities_update',
            'data': event['opportunities']
        }))

    async def send_price_update(self, event):
        """Send price updates"""
        await self.send(text_data=json.dumps({
            'type': 'price_update',
            'data': event['price_data']
        }))
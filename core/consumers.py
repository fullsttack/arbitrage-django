import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from core.redis_manager import redis_manager

logger = logging.getLogger(__name__)

class ArbitrageConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor_task = None

    async def connect(self):
        """Connect to WebSocket"""
        await self.channel_layer.group_add('arbitrage_updates', self.channel_name)
        await self.accept()
        
        # Initialize Redis connection
        await redis_manager.connect()
        
        # Start Redis monitoring
        self.monitor_task = asyncio.create_task(self._monitor_redis())
        
        # Send initial data
        await self.send_initial_data()
        
        logger.info("ArbitrageConsumer connected")

    async def disconnect(self, close_code):
        """Disconnect from WebSocket"""
        await self.channel_layer.group_discard('arbitrage_updates', self.channel_name)
        
        if self.monitor_task:
            self.monitor_task.cancel()
        
        logger.info(f"ArbitrageConsumer disconnected: {close_code}")

    async def _monitor_redis(self):
        """Monitor Redis stats and send updates"""
        while True:
            try:
                # Get Redis statistics
                stats = await redis_manager.get_redis_stats()
                opportunities_count = await redis_manager.get_opportunities_count()
                prices_count = await redis_manager.get_active_prices_count()
                
                # Send stats update
                await self.send(text_data=json.dumps({
                    'type': 'redis_stats',
                    'data': {
                        'opportunities_count': opportunities_count,
                        'prices_count': prices_count,
                        'redis_memory': stats.get('memory_used', 'N/A'),
                        'redis_clients': stats.get('connected_clients', 0),
                        'redis_ops_per_sec': stats.get('operations_per_sec', 0),
                        'uptime': stats.get('uptime_seconds', 0)
                    }
                }))
                
                # Skip bulk price updates - individual updates come from exchange services
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Redis monitoring error: {e}")
                await asyncio.sleep(10)

    async def send_initial_data(self):
        """Send initial opportunities and prices"""
        try:
            # Get recent opportunities
            opportunities = await redis_manager.get_latest_opportunities(50)
            
            logger.info(f"Sending {len(opportunities)} initial opportunities")
            await self.send(text_data=json.dumps({
                'type': 'initial_opportunities',
                'data': opportunities
            }))
            
            # Get current prices
            prices = await redis_manager.get_all_current_prices()
            prices_list = []
            
            logger.info(f"Got {len(prices)} price keys from Redis: {list(prices.keys())}")
            
            for key, price_data in prices.items():
                # Convert key format "prices:exchange:symbol" to readable format
                parts = key.split(':')
                if len(parts) >= 3:
                    price_data['exchange'] = parts[1]
                    price_data['symbol'] = parts[2]
                    # Ensure bid_volume and ask_volume are present
                    price_data['bid_volume'] = price_data.get('bid_volume', 0)
                    price_data['ask_volume'] = price_data.get('ask_volume', 0)
                    prices_list.append(price_data)
                    logger.debug(f"Processed price: {price_data}")
            
            logger.info(f"Sending {len(prices_list)} initial prices to WebSocket")
            await self.send(text_data=json.dumps({
                'type': 'initial_prices',
                'data': prices_list
            }))
            
        except Exception as e:
            logger.error(f"Error sending initial data: {e}", exc_info=True)

    async def send_prices_update(self):
        """Send updated prices"""
        try:
            # Get current prices
            prices = await redis_manager.get_all_current_prices()
            prices_list = []
            
            logger.debug(f"Prices update: Got {len(prices)} price keys from Redis")
            
            for key, price_data in prices.items():
                # Convert key format "prices:exchange:symbol" to readable format
                parts = key.split(':')
                if len(parts) >= 3:
                    price_data['exchange'] = parts[1]
                    price_data['symbol'] = parts[2]
                    # Ensure bid_volume and ask_volume are present
                    price_data['bid_volume'] = price_data.get('bid_volume', 0)
                    price_data['ask_volume'] = price_data.get('ask_volume', 0)
                    prices_list.append(price_data)
            
            if prices_list:
                logger.debug(f"Sending {len(prices_list)} updated prices to WebSocket")
                await self.send(text_data=json.dumps({
                    'type': 'prices_update',
                    'data': prices_list
                }))
            else:
                logger.warning("No prices to send in update")
                
        except Exception as e:
            logger.error(f"Error sending prices update: {e}", exc_info=True)

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
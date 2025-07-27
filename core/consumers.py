import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from core.redis import redis_manager
from .config_manager import get_web_config, get_ws_close_code

logger = logging.getLogger(__name__)

class SimpleArbitrageConsumer(AsyncWebsocketConsumer):
    """🚀 Simple WebSocket Consumer for Arbitrage Updates"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = get_web_config('default')
        self.monitor_tasks = []

    async def connect(self):
        """🔌 Connect to WebSocket"""
        # Simple authentication check
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            logger.warning(f"❌ WebSocket denied: not authenticated")
            await self.close(code=get_ws_close_code('AUTH_REQUIRED'))
            return
        
        # Permission check based on config
        if self.config['require_superuser'] and not user.is_superuser:
            logger.warning(f"❌ WebSocket denied: not superuser")
            await self.close(code=get_ws_close_code('PERMISSION_DENIED'))
            return
            
        if self.config['require_staff'] and not user.is_staff:
            logger.warning(f"❌ WebSocket denied: not staff")
            await self.close(code=get_ws_close_code('PERMISSION_DENIED'))
            return
        
        # Accept connection
        await self.channel_layer.group_add('arbitrage_updates', self.channel_name)
        await self.accept()
        
        # Initialize Redis
        await redis_manager.connect()
        
        # Start monitoring tasks
        self.monitor_tasks = [
            asyncio.create_task(self._monitor_redis_stats()),
            asyncio.create_task(self._monitor_system_health())
        ]
        
        # Send initial data
        await self._send_initial_data()
        
        logger.info(f"✅ WebSocket connected: {user.username}")

    async def disconnect(self, close_code):
        """🔌 Disconnect from WebSocket"""
        # Cancel monitoring tasks
        for task in self.monitor_tasks:
            if not task.done():
                task.cancel()
        
        # Leave group
        await self.channel_layer.group_discard('arbitrage_updates', self.channel_name)
        
        logger.info(f"🔌 WebSocket disconnected: {close_code}")

    async def _monitor_redis_stats(self):
        """📊 Monitor Redis statistics"""
        while True:
            try:
                # Get Redis stats
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
                
                await asyncio.sleep(self.config['redis_stats_interval'])
                
            except Exception as e:
                logger.error(f"❌ Redis stats error: {e}")
                await asyncio.sleep(self.config['redis_stats_interval'] * 2)

    async def _monitor_system_health(self):
        """🏥 Monitor system health"""
        while True:
            try:
                # Get exchange status and health summary
                exchange_status = await redis_manager.get_exchange_status()
                health_summary = await redis_manager.get_health_summary()
                
                # Send health update
                await self.send(text_data=json.dumps({
                    'type': 'system_health',
                    'data': {
                        'exchange_status': exchange_status,
                        'health_summary': health_summary,
                        'timestamp': health_summary.get('timestamp', 0)
                    }
                }))
                
                await asyncio.sleep(self.config['connection_health_interval'])
                
            except Exception as e:
                logger.error(f"❌ System health error: {e}")
                await asyncio.sleep(self.config['connection_health_interval'] * 2)

    async def _send_initial_data(self):
        """📤 Send initial data to client"""
        try:
            # Send initial opportunities
            opportunities = await redis_manager.get_latest_opportunities(
                self.config.get('opportunities_limit', -1)
            )
            
            await self.send(text_data=json.dumps({
                'type': 'initial_opportunities',
                'data': opportunities,
                'count': len(opportunities),
                'limit': self.config.get('opportunities_limit', -1)
            }))
            
            # Send initial prices
            prices = await redis_manager.get_all_prices()
            prices_list = []
            
            for key, price_data in prices.items():
                parts = key.split(':')
                if len(parts) >= 3:
                    price_data['exchange'] = parts[1]
                    price_data['symbol'] = parts[2]
                    prices_list.append(price_data)
            
            # Limit prices for performance
            if len(prices_list) > self.config['prices_limit']:
                prices_list = prices_list[:self.config['prices_limit']]
            
            await self.send(text_data=json.dumps({
                'type': 'initial_prices',
                'data': prices_list,
                'count': len(prices_list),
                'limit': self.config['prices_limit']
            }))
            
            # Send best opportunity
            best_opportunity = await redis_manager.get_highest_profit_opportunity()
            if best_opportunity:
                await self.send(text_data=json.dumps({
                    'type': 'best_opportunity',
                    'data': best_opportunity
                }))
            
            # Send exchange status
            exchange_status = await redis_manager.get_exchange_status()
            await self.send(text_data=json.dumps({
                'type': 'exchange_status',
                'data': exchange_status
            }))
            
            logger.debug(f"📤 Initial data sent: {len(opportunities)} opportunities, {len(prices_list)} prices")
            
        except Exception as e:
            logger.error(f"❌ Initial data error: {e}")

    # Event handlers for group messages
    async def send_opportunities(self, event):
        """🎯 Handle new opportunities"""
        await self.send(text_data=json.dumps({
            'type': 'opportunities_update',
            'data': event['opportunities']
        }))

    async def send_price_update(self, event):
        """💰 Handle price updates"""
        await self.send(text_data=json.dumps({
            'type': 'price_update',
            'data': event['price_data']
        }))

    async def send_system_alert(self, event):
        """🚨 Handle system alerts"""
        await self.send(text_data=json.dumps({
            'type': 'system_alert',
            'data': event['alert_data']
        }))

# Legacy compatibility
class ArbitrageConsumer(SimpleArbitrageConsumer):
    """📊 Legacy consumer class for compatibility"""
    pass
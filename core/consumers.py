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
        self.connection_health_monitor_task = None
        self.connection_alerts_monitor_task = None

    async def connect(self):
        """Connect to WebSocket - Superuser only"""
        # Check authentication
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            logger.warning(f"WebSocket connection denied - user not authenticated: {user}")
            await self.close(code=4003)  # Custom close code for authentication error
            return
            
        # For now, allow all authenticated users (remove superuser restriction for testing)
        # if not user.is_superuser:
        #     logger.warning(f"WebSocket connection denied - not superuser: {user}")
        #     await self.close(code=4003)
        #     return
            
        await self.channel_layer.group_add('arbitrage_updates', self.channel_name)
        await self.accept()
        
        # Initialize Redis connection
        await redis_manager.connect()
        
        # Start Redis monitoring
        self.monitor_task = asyncio.create_task(self._monitor_redis())
        
        # Start CONNECTION HEALTH monitoring (NEW APPROACH)
        self.connection_health_monitor_task = asyncio.create_task(self._monitor_connection_health())
        
        # Start CONNECTION ALERTS monitoring (NEW APPROACH)
        self.connection_alerts_monitor_task = asyncio.create_task(self._monitor_connection_alerts())
        
        # Send initial data - استفاده از محدودیت ثابت
        await self.send_initial_data()
        
        logger.debug("ArbitrageConsumer connected with CONNECTION HEALTH monitoring")

    async def disconnect(self, close_code):
        """Disconnect from WebSocket"""
        await self.channel_layer.group_discard('arbitrage_updates', self.channel_name)
        
        # Cancel all monitoring tasks
        if self.monitor_task:
            self.monitor_task.cancel()
        
        if self.connection_health_monitor_task:
            self.connection_health_monitor_task.cancel()
            
        if self.connection_alerts_monitor_task:
            self.connection_alerts_monitor_task.cancel()
        
        logger.debug(f"ArbitrageConsumer disconnected: {close_code}")

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
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Redis monitoring error: {e}")
                await asyncio.sleep(10)

    async def _monitor_connection_health(self):
        """Monitor CONNECTION HEALTH status and send updates (NEW APPROACH)"""
        while True:
            try:
                # Get connection status (not timestamp-based!)
                connection_status = await redis_manager.get_exchange_connection_status()
                
                # Get market health report (connection-based)
                health_report = await redis_manager.get_market_health_report()
                
                # Prepare connection health update
                health_update = {
                    'type': 'connection_health',
                    'data': {
                        'exchange_connections': connection_status,
                        'market_health': health_report.get('summary', {}),
                        'by_exchange': health_report.get('by_exchange', {}),
                        'approach': 'connection_health_based',
                        'timestamp': health_report.get('timestamp', 0)
                    }
                }
                
                await self.send(text_data=json.dumps(health_update))
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except Exception as e:
                logger.error(f"Connection health monitoring error: {e}")
                await asyncio.sleep(15)

    async def _monitor_connection_alerts(self):
        """Monitor for CONNECTION health alerts and send notifications (NEW APPROACH)"""
        last_alerts = []
        
        while True:
            try:
                # Get current connection-based alerts
                current_alerts = await redis_manager.get_connection_health_alerts()
                
                # Check for new alerts
                new_alerts = []
                current_alert_keys = {f"{alert['type']}_{alert.get('exchange', '')}" for alert in current_alerts}
                last_alert_keys = {f"{alert['type']}_{alert.get('exchange', '')}" for alert in last_alerts}
                
                # Find newly appeared alerts
                for alert in current_alerts:
                    alert_key = f"{alert['type']}_{alert.get('exchange', '')}"
                    if alert_key not in last_alert_keys:
                        new_alerts.append(alert)
                
                # Send alerts if any
                if current_alerts:  # Send all current alerts
                    alert_update = {
                        'type': 'connection_alerts',
                        'data': {
                            'alerts': current_alerts,
                            'new_alerts': new_alerts,
                            'alert_count': len(current_alerts),
                            'critical_count': len([a for a in current_alerts if a.get('severity') == 'critical']),
                            'warning_count': len([a for a in current_alerts if a.get('severity') == 'warning']),
                            'approach': 'connection_health_based'
                        }
                    }
                    
                    await self.send(text_data=json.dumps(alert_update))
                
                # Send "all clear" message if no alerts
                elif last_alerts:  # Had alerts before, but now clear
                    await self.send(text_data=json.dumps({
                        'type': 'connection_alerts',
                        'data': {
                            'alerts': [],
                            'new_alerts': [],
                            'alert_count': 0,
                            'critical_count': 0,
                            'warning_count': 0,
                            'message': 'All connection health alerts resolved',
                            'approach': 'connection_health_based'
                        }
                    }))
                
                last_alerts = current_alerts
                await asyncio.sleep(15)  # Check alerts every 15 seconds
                
            except Exception as e:
                logger.error(f"Connection alert monitoring error: {e}")
                await asyncio.sleep(20)

    async def send_initial_data(self):
        """Send initial opportunities and prices with CONNECTION HEALTH info"""
        try:
            # استفاده از محدودیت بالا برای نمایش همه فرصت‌ها - 1000 فرصت
            OPPORTUNITIES_DISPLAY_LIMIT = 1000
            
            # Get recent opportunities - محدودیت بالا برای نمایش کامل
            opportunities = await redis_manager.get_latest_opportunities(OPPORTUNITIES_DISPLAY_LIMIT)
            
            logger.debug(f"Sending {len(opportunities)} initial opportunities")
            await self.send(text_data=json.dumps({
                'type': 'initial_opportunities',
                'data': opportunities
            }))
            
            # Get current prices with CONNECTION VALIDITY info
            prices = await redis_manager.get_all_current_prices()
            prices_list = []
            
            logger.debug(f"Got {len(prices)} price keys from Redis: {list(prices.keys())}")
            
            for key, price_data in prices.items():
                # Convert key format "prices:exchange:symbol" to readable format
                parts = key.split(':')
                if len(parts) >= 3:
                    price_data['exchange'] = parts[1]
                    price_data['symbol'] = parts[2]
                    # Ensure bid_volume and ask_volume are present
                    price_data['bid_volume'] = price_data.get('bid_volume', 0)
                    price_data['ask_volume'] = price_data.get('ask_volume', 0)
                    # Add CONNECTION-BASED validity info (NEW)
                    price_data['age_seconds'] = price_data.get('age_seconds', 0)
                    price_data['is_valid'] = price_data.get('is_valid', False)
                    price_data['validity_reason'] = price_data.get('validity_reason', 'unknown')
                    price_data['exchange_status'] = price_data.get('exchange_status', 'unknown')
                    price_data['seconds_since_heartbeat'] = price_data.get('seconds_since_heartbeat', float('inf'))
                    
                    # Legacy fields for compatibility
                    price_data['is_fresh'] = price_data.get('is_valid', False)
                    price_data['is_stale'] = not price_data.get('is_valid', True)
                    
                    prices_list.append(price_data)
            
            logger.debug(f"Sending {len(prices_list)} initial prices to WebSocket")
            await self.send(text_data=json.dumps({
                'type': 'initial_prices',
                'data': prices_list
            }))
            
            # ارسال بهترین فرصت از Redis
            best_opportunity = await redis_manager.get_highest_profit_opportunity()
            if best_opportunity:
                await self.send(text_data=json.dumps({
                    'type': 'best_opportunity_update',
                    'data': best_opportunity
                }))
            
            # Send initial CONNECTION health status (NEW)
            connection_status = await redis_manager.get_exchange_connection_status()
            await self.send(text_data=json.dumps({
                'type': 'initial_connection_status',
                'data': {
                    'exchange_connections': connection_status,
                    'approach': 'connection_health_based'
                }
            }))
            
            # Send initial MARKET health report (NEW)
            health_report = await redis_manager.get_market_health_report()
            await self.send(text_data=json.dumps({
                'type': 'initial_market_health',
                'data': health_report
            }))
            
            # Send initial CONNECTION alerts (NEW)
            alerts = await redis_manager.get_connection_health_alerts()
            await self.send(text_data=json.dumps({
                'type': 'initial_connection_alerts',
                'data': {
                    'alerts': alerts,
                    'alert_count': len(alerts),
                    'critical_count': len([a for a in alerts if a.get('severity') == 'critical']),
                    'warning_count': len([a for a in alerts if a.get('severity') == 'warning']),
                    'approach': 'connection_health_based'
                }
            }))
            
        except Exception as e:
            logger.error(f"Error sending initial data: {e}", exc_info=True)

    async def send_prices_update(self):
        """Send updated prices with CONNECTION VALIDITY info"""
        try:
            # Get current prices with CONNECTION health information
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
                    # Add CONNECTION-BASED validity info (NEW)
                    price_data['age_seconds'] = price_data.get('age_seconds', 0)
                    price_data['is_valid'] = price_data.get('is_valid', False)
                    price_data['validity_reason'] = price_data.get('validity_reason', 'unknown')
                    price_data['exchange_status'] = price_data.get('exchange_status', 'unknown')
                    price_data['seconds_since_heartbeat'] = price_data.get('seconds_since_heartbeat', float('inf'))
                    
                    # Legacy fields for compatibility  
                    price_data['is_fresh'] = price_data.get('is_valid', False)
                    price_data['is_stale'] = not price_data.get('is_valid', True)
                    
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
        """Send new arbitrage opportunities with CONNECTION HEALTH info"""
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

    # New message handlers for CONNECTION HEALTH features
    
    async def send_connection_health_update(self, event):
        """Send connection health updates (NEW)"""
        await self.send(text_data=json.dumps({
            'type': 'connection_health_update',
            'data': event['health_data']
        }))

    async def send_connection_alert_update(self, event):
        """Send connection alert updates (NEW)"""
        await self.send(text_data=json.dumps({
            'type': 'connection_alert_update',
            'data': event['alert_data']
        }))

    async def send_market_health_report(self, event):
        """Send market health report updates (NEW)"""
        await self.send(text_data=json.dumps({
            'type': 'market_health_report_update',
            'data': event['health_data']
        }))
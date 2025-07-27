import json
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from decimal import Decimal
import redis.asyncio as redis
from django.conf import settings
from ..config_manager import get_redis_config

logger = logging.getLogger(__name__)

class SimpleRedisManager:
    """🚀 Simple and Fast Redis Manager"""
    
    def __init__(self, config_profile: str = 'default'):
        self.config = get_redis_config(config_profile)
        self.redis_client = None
        self.is_connected = False
        
        logger.info(f"✅ Redis Manager initialized with {config_profile} profile")

    async def connect(self):
        """🔌 Initialize Redis connection"""
        if not self.redis_client:
            self.redis_client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                password=getattr(settings, 'REDIS_PASSWORD', None),
                decode_responses=True
            )
            self.is_connected = True
            logger.debug("🔌 Redis connected successfully")

    async def save_price_data(self, exchange: str, symbol: str, bid_price: float, ask_price: float, 
                             bid_volume: float = 0, ask_volume: float = 0):
        """💰 Save price data with TTL"""
        timestamp = time.time()
        
        price_data = {
            'exchange': exchange,
            'symbol': symbol,
            'bid_price': float(bid_price),
            'ask_price': float(ask_price),
            'bid_volume': float(bid_volume),
            'ask_volume': float(ask_volume),
            'timestamp': timestamp
        }
        
        # Use pipeline for efficiency
        pipeline = self.redis_client.pipeline()
        
        # Save price with TTL
        price_key = f"price:{exchange}:{symbol}"
        pipeline.setex(price_key, self.config['price_ttl'], json.dumps(price_data))
        
        # Update heartbeat
        heartbeat_key = f"heartbeat:{exchange}"
        heartbeat_data = {'exchange': exchange, 'timestamp': timestamp}
        pipeline.setex(heartbeat_key, self.config['heartbeat_ttl'], json.dumps(heartbeat_data))
        
        await pipeline.execute()

    async def get_all_prices(self) -> Dict[str, Any]:
        """💰 Get all current prices"""
        price_keys = await self.redis_client.keys("price:*")
        if not price_keys:
            return {}
        
        # Use pipeline for efficiency
        pipeline = self.redis_client.pipeline()
        for key in price_keys:
            pipeline.get(key)
        
        price_data_list = await pipeline.execute()
        
        prices = {}
        current_time = time.time()
        
        for key, data in zip(price_keys, price_data_list):
            if data:
                try:
                    price_info = json.loads(data)
                    # Add age info
                    price_info['age_seconds'] = current_time - price_info['timestamp']
                    prices[key] = price_info
                except Exception as e:
                    logger.debug(f"❌ Error processing price {key}: {e}")
        
        return prices

    async def get_valid_prices(self) -> Dict[str, Any]:
        """💰 Get only valid (non-expired) prices"""
        # Redis handles TTL automatically, so all returned prices are valid
        return await self.get_all_prices()

    async def get_exchange_status(self) -> Dict[str, Any]:
        """📊 Get exchange connection status"""
        heartbeat_keys = await self.redis_client.keys("heartbeat:*")
        status = {}
        current_time = time.time()
        
        for key in heartbeat_keys:
            exchange_name = key.split(':')[1]
            data = await self.redis_client.get(key)
            
            if data:
                try:
                    heartbeat_data = json.loads(data)
                    last_heartbeat = heartbeat_data.get('timestamp', 0)
                    seconds_since = current_time - last_heartbeat
                    
                    status[exchange_name] = {
                        'status': 'online' if seconds_since < self.config['offline_threshold'] else 'offline',
                        'last_heartbeat': last_heartbeat,
                        'seconds_since': seconds_since
                    }
                except Exception as e:
                    logger.debug(f"❌ Error parsing heartbeat for {exchange_name}: {e}")
                    status[exchange_name] = {'status': 'offline', 'last_heartbeat': 0, 'seconds_since': float('inf')}
        
        return status

    async def save_arbitrage_opportunity(self, opportunity: Dict[str, Any]):
        """🎯 Save arbitrage opportunity"""
        timestamp = time.time()
        
        # Create simple unique ID
        unique_id = f"{opportunity.get('buy_exchange')}_{opportunity.get('sell_exchange')}_{opportunity.get('symbol')}_{int(timestamp * 1000)}"
        
        opportunity['id'] = unique_id
        opportunity['timestamp'] = timestamp
        
        # Use pipeline for efficiency
        pipeline = self.redis_client.pipeline()
        
        # Save opportunity
        opp_key = f"opportunity:{unique_id}"
        pipeline.setex(opp_key, self.config['old_opportunity_threshold'], json.dumps(opportunity))
        
        # Add to sorted set for latest retrieval
        pipeline.zadd("opportunities:latest", {opp_key: timestamp})
        
        # Keep only max opportunities
        pipeline.zremrangebyrank("opportunities:latest", 0, -(self.config['max_opportunities'] + 1))
        
        await pipeline.execute()
        
        return unique_id

    async def get_latest_opportunities(self, limit: int = None) -> List[Dict[str, Any]]:
        """🎯 Get latest arbitrage opportunities"""
        # Get all opportunity keys - no limit
        keys = await self.redis_client.zrevrange("opportunities:latest", 0, -1)
        
        if not keys:
            return []
        
        # Use pipeline for efficiency
        pipeline = self.redis_client.pipeline()
        for key in keys:
            pipeline.get(key)
        
        data_list = await pipeline.execute()
        
        opportunities = []
        for data in data_list:
            if data:
                try:
                    opportunity = json.loads(data)
                    opportunities.append(opportunity)
                except Exception as e:
                    logger.debug(f"❌ Error parsing opportunity: {e}")
        
        return opportunities

    async def get_opportunities_count(self) -> int:
        """🎯 Get total opportunities count"""
        return await self.redis_client.zcard("opportunities:latest")

    async def get_active_prices_count(self) -> int:
        """💰 Get active prices count"""
        price_keys = await self.redis_client.keys("price:*")
        return len(price_keys)

    async def get_highest_profit_opportunity(self) -> Optional[Dict[str, Any]]:
        """🎯 Get highest profit opportunity"""
        opportunities = await self.get_latest_opportunities(100)  # Check more for accuracy
        
        if not opportunities:
            return None
        
        # Find max profit
        max_profit = -float('inf')
        best_opportunity = None
        
        for opp in opportunities:
            profit = opp.get('profit_percentage', 0)
            if isinstance(profit, (int, float)) and profit > max_profit:
                max_profit = profit
                best_opportunity = opp
        
        return best_opportunity

    async def get_redis_stats(self) -> Dict[str, Any]:
        """📊 Get Redis statistics"""
        try:
            info = await self.redis_client.info()
            return {
                'memory_used': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0),
                'operations_per_sec': info.get('instantaneous_ops_per_sec', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'uptime_seconds': info.get('uptime_in_seconds', 0)
            }
        except Exception as e:
            logger.error(f"❌ Error getting Redis stats: {e}")
            return {}

    async def cleanup_old_data(self):
        """🧹 Cleanup old data"""
        current_time = time.time()
        
        # Clean old opportunities from sorted set
        cutoff_time = current_time - self.config['old_opportunity_threshold']
        
        # Remove old opportunities from sorted set
        old_count = await self.redis_client.zremrangebyscore("opportunities:latest", 0, cutoff_time)
        
        # Clean individual opportunity keys (Redis TTL handles this automatically, but we can force cleanup)
        opp_keys = await self.redis_client.keys("opportunity:*")
        cleaned_opps = 0
        
        # Process in batches
        batch_size = self.config['batch_size']
        for i in range(0, len(opp_keys), batch_size):
            batch_keys = opp_keys[i:i+batch_size]
            
            pipeline = self.redis_client.pipeline()
            for key in batch_keys:
                pipeline.get(key)
            
            batch_data = await pipeline.execute()
            
            # Check which ones are old
            keys_to_delete = []
            for key, data in zip(batch_keys, batch_data):
                if data:
                    try:
                        opp_data = json.loads(data)
                        if current_time - opp_data.get('timestamp', current_time) > self.config['old_opportunity_threshold']:
                            keys_to_delete.append(key)
                    except:
                        keys_to_delete.append(key)  # Delete corrupted data
                else:
                    keys_to_delete.append(key)  # Delete empty keys
            
            if keys_to_delete:
                await self.redis_client.delete(*keys_to_delete)
                cleaned_opps += len(keys_to_delete)
        
        # Note: Prices and heartbeats are automatically cleaned by Redis TTL
        
        if old_count > 0 or cleaned_opps > 0:
            logger.debug(f"🧹 Cleanup: {old_count} old opportunities from sorted set, {cleaned_opps} opportunity keys")

    async def clear_all_data(self):
        """🗑️ Clear all data (for testing)"""
        # Clear all arbitrage data
        await self.redis_client.delete("opportunities:latest")
        
        # Clear all keys by pattern
        for pattern in ["price:*", "opportunity:*", "heartbeat:*"]:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
        
        logger.debug("🗑️ All Redis data cleared")

    async def get_health_summary(self) -> Dict[str, Any]:
        """📊 Get simple health summary"""
        try:
            exchange_status = await self.get_exchange_status()
            prices_count = await self.get_active_prices_count()
            opportunities_count = await self.get_opportunities_count()
            
            online_exchanges = sum(1 for status in exchange_status.values() if status['status'] == 'online')
            total_exchanges = len(exchange_status)
            
            return {
                'timestamp': time.time(),
                'exchanges': {
                    'online': online_exchanges,
                    'total': total_exchanges,
                    'status': exchange_status
                },
                'data': {
                    'prices': prices_count,
                    'opportunities': opportunities_count
                },
                'config_profile': self.config.get('profile', 'unknown')
            }
        except Exception as e:
            logger.error(f"❌ Error getting health summary: {e}")
            return {'error': str(e)}

    async def close(self):
        """🔌 Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False
            logger.debug("🔌 Redis connection closed")

# Create global instance with default config
redis_manager = SimpleRedisManager()

# Legacy compatibility - can be configured later
async def init_redis_manager(config_profile: str = 'default'):
    """🔧 Initialize Redis manager with specific config"""
    global redis_manager
    redis_manager = SimpleRedisManager(config_profile)
    await redis_manager.connect()
    return redis_manager
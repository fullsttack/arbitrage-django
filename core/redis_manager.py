import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
import redis.asyncio as redis
from django.conf import settings

logger = logging.getLogger(__name__)

class RedisManager:
    """Redis Manager for handling prices and arbitrage opportunities only"""
    
    def __init__(self):
        self.redis_client = None
        self.is_connected = False
        
    async def connect(self):
        """Initialize Redis connection"""
        if not self.redis_client:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True
            )
            self.is_connected = True
            logger.info("Redis connected successfully")
    
    async def save_price_data(self, exchange: str, symbol: str, bid_price: float, ask_price: float, 
                             bid_volume: float = 0, ask_volume: float = 0):
        """Save price data to Redis"""
        timestamp = asyncio.get_event_loop().time()
        
        price_data = {
            'exchange': exchange,
            'symbol': symbol,
            'bid_price': float(bid_price),
            'ask_price': float(ask_price),
            'bid_volume': float(bid_volume),  # buy volume
            'ask_volume': float(ask_volume),  # sell volume
            'timestamp': timestamp
        }
        
        # Save price data - keep last price until new update arrives
        key = f"prices:{exchange}:{symbol}"
        await self.redis_client.set(key, json.dumps(price_data))  # No TTL - keep last price
        
        logger.debug(f"Price saved: {exchange} {symbol} - bid:{bid_price}, ask:{ask_price}")
    
    async def get_all_current_prices(self) -> Dict[str, Any]:
        """Get all current prices from Redis"""
        keys = await self.redis_client.keys("prices:*")
        prices = {}
        
        for key in keys:
            data = await self.redis_client.get(key)
            if data:
                try:
                    price_info = json.loads(data)
                    prices[key] = price_info
                except:
                    continue
        
        return prices
    
    async def get_prices_by_exchange(self, exchange: str) -> Dict[str, Any]:
        """Get all prices for a specific exchange"""
        keys = await self.redis_client.keys(f"prices:{exchange}:*")
        prices = {}
        
        for key in keys:
            data = await self.redis_client.get(key)
            if data:
                try:
                    price_info = json.loads(data)
                    symbol = key.split(':')[-1]
                    prices[symbol] = price_info
                except:
                    continue
        
        return prices
    
    async def save_arbitrage_opportunity(self, opportunity: Dict[str, Any]):
        """Save arbitrage opportunity to Redis"""
        timestamp = asyncio.get_event_loop().time()
        opportunity['timestamp'] = timestamp
        opportunity['id'] = f"{timestamp}_{opportunity.get('buy_exchange')}_{opportunity.get('sell_exchange')}_{opportunity.get('symbol')}"
        
        # Save individual opportunity
        key = f"opportunity:{opportunity['id']}"
        await self.redis_client.setex(key, 300, json.dumps(opportunity))  # TTL 5 minutes
        
        # Add to sorted set for easy retrieval
        await self.redis_client.zadd("opportunities:latest", {key: timestamp})
        
        # Keep only latest 500 opportunities
        await self.redis_client.zremrangebyrank("opportunities:latest", 0, -501)
        
        logger.info(f"Arbitrage opportunity saved: {opportunity.get('symbol')} - {opportunity.get('profit_percentage', 0):.2f}% profit")
    
    async def get_latest_opportunities(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get latest arbitrage opportunities"""
        # Get latest opportunity keys
        keys = await self.redis_client.zrevrange("opportunities:latest", 0, limit-1)
        
        opportunities = []
        for key in keys:
            data = await self.redis_client.get(key)
            if data:
                try:
                    opportunities.append(json.loads(data))
                except:
                    continue
        
        return opportunities
    
    async def get_opportunities_count(self) -> int:
        """Get total count of current opportunities"""
        return await self.redis_client.zcard("opportunities:latest")
    
    async def get_active_prices_count(self) -> int:
        """Get count of active prices"""
        keys = await self.redis_client.keys("prices:*")
        return len(keys)
    
    async def get_redis_stats(self) -> Dict[str, Any]:
        """Get Redis statistics"""
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
            logger.error(f"Error getting Redis stats: {e}")
            return {}
    
    async def cleanup_old_data(self):
        """Clean up old price data and opportunities"""
        current_time = asyncio.get_event_loop().time()
        
        # Clean old prices (older than 1 hour - keep last prices available)
        price_keys = await self.redis_client.keys("prices:*")
        cleaned_prices = 0
        
        for key in price_keys:
            data = await self.redis_client.get(key)
            if data:
                try:
                    price_data = json.loads(data)
                    # Only clean very old prices (older than 1 hour)
                    if current_time - price_data['timestamp'] > 3600:
                        await self.redis_client.delete(key)
                        cleaned_prices += 1
                except:
                    # Only delete corrupted data
                    await self.redis_client.delete(key)
                    cleaned_prices += 1
        
        # Clean old opportunities (older than 10 minutes)
        old_opportunities = await self.redis_client.zrangebyscore(
            "opportunities:latest", 0, current_time - 600
        )
        
        if old_opportunities:
            # Remove from sorted set
            await self.redis_client.zrem("opportunities:latest", *old_opportunities)
            # Remove individual keys
            await self.redis_client.delete(*old_opportunities)
        
        if cleaned_prices > 0 or old_opportunities:
            logger.info(f"Cleaned {cleaned_prices} old prices, {len(old_opportunities)} old opportunities")
    
    async def clear_all_data(self):
        """Clear all price and opportunity data (for testing)"""
        # Clear all prices
        price_keys = await self.redis_client.keys("prices:*")
        if price_keys:
            await self.redis_client.delete(*price_keys)
        
        # Clear all opportunities
        opp_keys = await self.redis_client.keys("opportunity:*")
        if opp_keys:
            await self.redis_client.delete(*opp_keys)
        
        await self.redis_client.delete("opportunities:latest")
        
        logger.info("All Redis data cleared")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False

# Global Redis Manager instance
redis_manager = RedisManager()
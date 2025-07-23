import json
import asyncio
import logging
import time
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
        timestamp = time.time()  # Use actual unix timestamp
        
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
        """Save or update arbitrage opportunity to Redis (avoid duplicates)"""
        timestamp = time.time()  # Use actual unix timestamp
        
        # Simple storage without deduplication - save all opportunities
        symbol = opportunity.get('symbol')
        buy_exchange = opportunity.get('buy_exchange')
        sell_exchange = opportunity.get('sell_exchange')
        
        # Create unique key with timestamp
        timestamp_ms = int(timestamp * 1000)
        unique_id = f"{buy_exchange}_{sell_exchange}_{symbol}_{timestamp_ms}"
        
        opportunity['timestamp'] = timestamp
        opportunity['id'] = unique_id
        opportunity['last_updated'] = timestamp
        
        # Use timestamp-based key for complete uniqueness  
        key = f"opportunity:{unique_id}"
        
        logger.debug(f"Saving opportunity: {symbol} - {opportunity.get('profit_percentage', 0):.2f}% profit")
        
        # Save opportunity (no TTL - keep until 24 hours cleanup)
        await self.redis_client.set(key, json.dumps(opportunity))
        
        # Add/update in sorted set for easy retrieval
        await self.redis_client.zadd("opportunities:latest", {key: timestamp})
        
        # Keep only latest 10000 opportunities to see more data
        await self.redis_client.zremrangebyrank("opportunities:latest", 0, -10001)
    
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
    
    async def get_highest_profit_opportunity(self) -> Optional[Dict[str, Any]]:
        """Get the opportunity with the highest profit percentage from ALL opportunities"""
        try:
            # Get all opportunity keys directly - don't rely on sorted set limit
            opportunity_keys = await self.redis_client.keys("opportunity:*")
            
            if not opportunity_keys:
                return None
            
            highest_profit_opp = None
            highest_profit = -float('inf')
            
            # Check all opportunities to find the true maximum
            for key in opportunity_keys:
                data = await self.redis_client.get(key)
                if data:
                    try:
                        opp_data = json.loads(data)
                        profit_percentage = opp_data.get('profit_percentage', 0)
                        
                        if isinstance(profit_percentage, (int, float)) and profit_percentage > highest_profit:
                            highest_profit = profit_percentage
                            highest_profit_opp = opp_data
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue
            
            return highest_profit_opp
            
        except Exception as e:
            logger.error(f"Error getting highest profit opportunity: {e}")
            return None
    
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
        current_time = time.time()  # Use actual unix timestamp
        
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
        
        # Clean old opportunities (older than 24 hours)
        old_opportunities = await self.redis_client.zrangebyscore(
            "opportunities:latest", 0, current_time - 86400
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
import json
import asyncio
import logging
import time
import hashlib
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
    
    def _create_opportunity_composite_key(self, opportunity: Dict[str, Any]) -> str:
        """Create unique composite key based on opportunity characteristics"""
        key_parts = [
            opportunity.get('buy_exchange', ''),
            opportunity.get('sell_exchange', ''),
            opportunity.get('symbol', ''),
            f"{opportunity.get('buy_price', 0):.10f}",
            f"{opportunity.get('sell_price', 0):.10f}",
            f"{opportunity.get('buy_volume', 0):.8f}",
            f"{opportunity.get('sell_volume', 0):.8f}"
        ]
        
        # Create composite string
        composite_string = "|".join(key_parts)
        
        # Create hash for shorter key
        hash_object = hashlib.sha256(composite_string.encode())
        return hash_object.hexdigest()[:16]  # 16 character hash
    
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
        """Save arbitrage opportunity with duplicate detection"""
        timestamp = time.time()
        
        # Create composite key for duplicate detection
        composite_key = self._create_opportunity_composite_key(opportunity)
        
        # Check if this exact opportunity already exists
        existing_key = f"opportunity:active:{composite_key}"
        existing_data = await self.redis_client.get(existing_key)
        
        if existing_data:
            # Opportunity already exists - update metadata only
            try:
                existing_opportunity = json.loads(existing_data)
                existing_opportunity['last_seen'] = timestamp
                existing_opportunity['seen_count'] = existing_opportunity.get('seen_count', 1) + 1
                
                # Update the existing opportunity
                await self.redis_client.set(existing_key, json.dumps(existing_opportunity))
                
                # Update timestamp in sorted set for ordering
                await self.redis_client.zadd("opportunities:latest", {existing_key: timestamp})
                
                logger.debug(f"Updated existing opportunity: {opportunity.get('symbol')} - seen {existing_opportunity['seen_count']} times")
                return "UPDATED", existing_opportunity['id']
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error updating existing opportunity: {e}, creating new one")
                # Fall through to create new opportunity
        
        # Create new opportunity
        # Create unique ID with timestamp for historical tracking
        timestamp_ms = int(timestamp * 1000)
        unique_id = f"{opportunity.get('buy_exchange')}_{opportunity.get('sell_exchange')}_{opportunity.get('symbol')}_{timestamp_ms}"
        
        opportunity['id'] = unique_id
        opportunity['composite_key'] = composite_key
        opportunity['timestamp'] = timestamp
        opportunity['created_at'] = timestamp
        opportunity['last_seen'] = timestamp
        opportunity['seen_count'] = 1
        
        # Save as active opportunity (for duplicate detection)
        await self.redis_client.set(existing_key, json.dumps(opportunity))
        
        # Also save with unique ID for historical tracking
        historical_key = f"opportunity:{unique_id}"
        await self.redis_client.set(historical_key, json.dumps(opportunity))
        
        # Add to sorted set for easy retrieval
        await self.redis_client.zadd("opportunities:latest", {existing_key: timestamp})
        
        # Keep only latest 10000 active opportunities for performance
        await self.redis_client.zremrangebyrank("opportunities:latest", 0, -10001)
        
        logger.debug(f"Created new opportunity: {opportunity.get('symbol')} - {opportunity.get('profit_percentage', 0):.2f}% profit")
        return "CREATED", unique_id
    
    async def get_latest_opportunities(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get latest arbitrage opportunities"""
        # Get latest opportunity keys from sorted set
        keys = await self.redis_client.zrevrange("opportunities:latest", 0, limit-1)
        
        opportunities = []
        for key in keys:
            data = await self.redis_client.get(key)
            if data:
                try:
                    opportunity = json.loads(data)
                    opportunities.append(opportunity)
                except:
                    continue
        
        return opportunities
    
    async def get_opportunities_count(self) -> int:
        """Get total count of current active opportunities"""
        return await self.redis_client.zcard("opportunities:latest")
    
    async def get_active_prices_count(self) -> int:
        """Get count of active prices"""
        keys = await self.redis_client.keys("prices:*")
        return len(keys)
    
    async def get_highest_profit_opportunity(self) -> Optional[Dict[str, Any]]:
        """Get the opportunity with the highest profit percentage from active opportunities"""
        try:
            # Get all active opportunity keys
            opportunity_keys = await self.redis_client.zrange("opportunities:latest", 0, -1)
            
            if not opportunity_keys:
                return None
            
            highest_profit_opp = None
            highest_profit = -float('inf')
            
            # Check all active opportunities to find the true maximum
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
        """Clean up old price data and opportunities (keep opportunities for 1 month)"""
        current_time = time.time()
        
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
        
        # Clean old opportunities (older than 1 month = 30 days = 2,592,000 seconds)
        one_month_ago = current_time - 2592000
        
        # Clean from active opportunities sorted set
        old_active_opportunities = await self.redis_client.zrangebyscore(
            "opportunities:latest", 0, one_month_ago
        )
        
        if old_active_opportunities:
            # Remove from sorted set
            await self.redis_client.zrem("opportunities:latest", *old_active_opportunities)
            # Remove individual active opportunity keys
            await self.redis_client.delete(*old_active_opportunities)
        
        # Clean historical opportunity records (older than 1 month)
        historical_keys = await self.redis_client.keys("opportunity:*")
        cleaned_historical = 0
        
        # Process in batches to avoid blocking Redis
        batch_size = 1000
        for i in range(0, len(historical_keys), batch_size):
            batch_keys = historical_keys[i:i+batch_size]
            
            # Check each historical opportunity
            pipeline = self.redis_client.pipeline()
            for key in batch_keys:
                pipeline.get(key)
            
            batch_data = await pipeline.execute()
            
            # Delete old historical opportunities
            keys_to_delete = []
            for key, data in zip(batch_keys, batch_data):
                if data:
                    try:
                        opp_data = json.loads(data)
                        # Check if it's historical (not active) and old
                        if (key.startswith("opportunity:") and 
                            not key.startswith("opportunity:active:") and
                            current_time - opp_data.get('timestamp', current_time) > 2592000):
                            keys_to_delete.append(key)
                    except:
                        # Delete corrupted data
                        keys_to_delete.append(key)
                else:
                    # Delete empty keys
                    keys_to_delete.append(key)
            
            if keys_to_delete:
                await self.redis_client.delete(*keys_to_delete)
                cleaned_historical += len(keys_to_delete)
        
        if cleaned_prices > 0 or old_active_opportunities or cleaned_historical > 0:
            logger.info(
                f"Cleanup completed - "
                f"Prices: {cleaned_prices}, "
                f"Active opportunities: {len(old_active_opportunities)}, "
                f"Historical opportunities: {cleaned_historical}"
            )
    
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
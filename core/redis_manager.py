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
    """Redis Manager with proper separation of Connection Health vs Price Validity"""
    
    def __init__(self):
        self.redis_client = None
        self.is_connected = False
        
        # NEW APPROACH: Separate Connection Health from Price Validity
        self.CONNECTION_HEARTBEAT_TTL = 90  # Connection heartbeat expires in 90 seconds
        self.PRICE_PERSISTENCE = True  # Prices persist until connection issues
        self.EXCHANGE_OFFLINE_THRESHOLD = 120  # 2 minutes without heartbeat = offline
        
        # Price validity settings (CONSERVATIVE)
        self.PRICE_INVALIDATION_THRESHOLD = 1800  # Only invalidate after 30 minutes of connection loss
        
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
        """Save price data with NO TTL - prices persist until connection issues"""
        timestamp = time.time()
        
        price_data = {
            'exchange': exchange,
            'symbol': symbol,
            'bid_price': float(bid_price),
            'ask_price': float(ask_price),
            'bid_volume': float(bid_volume),
            'ask_volume': float(ask_volume),
            'timestamp': timestamp,
            'last_update': timestamp
        }
        
        # Save price data with NO TTL - let it persist
        key = f"prices:{exchange}:{symbol}"
        await self.redis_client.set(key, json.dumps(price_data))
        
        # Update connection heartbeat with TTL
        await self._update_connection_heartbeat(exchange, timestamp)
        
        logger.debug(f"Price saved (persistent): {exchange} {symbol} - bid:{bid_price}, ask:{ask_price}")
    
    async def _update_connection_heartbeat(self, exchange: str, timestamp: float):
        """Update connection heartbeat - this has TTL to detect offline exchanges"""
        heartbeat_key = f"heartbeat:{exchange}"
        heartbeat_data = {
            'exchange': exchange,
            'last_heartbeat': timestamp,
            'status': 'online'
        }
        
        # Get existing heartbeat to preserve counters
        existing = await self.redis_client.get(heartbeat_key)
        if existing:
            try:
                existing_data = json.loads(existing)
                heartbeat_data['heartbeat_count'] = existing_data.get('heartbeat_count', 0) + 1
                heartbeat_data['connection_start'] = existing_data.get('connection_start', timestamp)
            except:
                heartbeat_data['heartbeat_count'] = 1
                heartbeat_data['connection_start'] = timestamp
        else:
            heartbeat_data['heartbeat_count'] = 1
            heartbeat_data['connection_start'] = timestamp
        
        # Heartbeat expires after 90 seconds - this is how we detect offline exchanges
        await self.redis_client.setex(heartbeat_key, self.CONNECTION_HEARTBEAT_TTL, json.dumps(heartbeat_data))
    
    async def get_all_current_prices(self) -> Dict[str, Any]:
        """Get all current prices with validity based on connection health"""
        keys = await self.redis_client.keys("prices:*")
        prices = {}
        current_time = time.time()
        
        # Get exchange connection status
        exchange_status = await self.get_exchange_connection_status()
        
        for key in keys:
            data = await self.redis_client.get(key)
            if data:
                try:
                    price_info = json.loads(data)
                    exchange = price_info.get('exchange')
                    
                    # Determine price validity based on EXCHANGE CONNECTION STATUS, not timestamp
                    exchange_info = exchange_status.get(exchange, {})
                    is_exchange_online = exchange_info.get('status') == 'online'
                    seconds_since_heartbeat = exchange_info.get('seconds_since_heartbeat', float('inf'))
                    
                    # Price is valid if:
                    # 1. Exchange is currently online, OR
                    # 2. Exchange went offline recently (less than invalidation threshold)
                    price_age = current_time - price_info['timestamp']
                    
                    if is_exchange_online:
                        # Exchange is online - price is definitely valid regardless of age
                        is_valid = True
                        validity_reason = "exchange_online"
                    elif seconds_since_heartbeat <= self.PRICE_INVALIDATION_THRESHOLD:
                        # Exchange offline but recently - price still valid
                        is_valid = True
                        validity_reason = f"recent_offline_{seconds_since_heartbeat:.0f}s"
                    else:
                        # Exchange offline for too long - price invalid
                        is_valid = False
                        validity_reason = f"long_offline_{seconds_since_heartbeat:.0f}s"
                    
                    # Add validity information
                    price_info['age_seconds'] = price_age
                    price_info['is_valid'] = is_valid
                    price_info['validity_reason'] = validity_reason
                    price_info['exchange_status'] = exchange_info.get('status', 'unknown')
                    price_info['seconds_since_heartbeat'] = seconds_since_heartbeat
                    
                    # Legacy compatibility (deprecated)
                    price_info['is_fresh'] = is_valid
                    price_info['is_stale'] = not is_valid
                    
                    prices[key] = price_info
                except Exception as e:
                    logger.debug(f"Error processing price {key}: {e}")
                    continue
        
        return prices
    
    async def get_valid_prices_only(self) -> Dict[str, Any]:
        """Get only valid prices (based on connection health, not timestamp)"""
        all_prices = await self.get_all_current_prices()
        valid_prices = {}
        
        for key, price_data in all_prices.items():
            if price_data.get('is_valid', False):
                valid_prices[key] = price_data
        
        logger.debug(f"Valid prices: {len(valid_prices)}/{len(all_prices)} based on connection health")
        return valid_prices
    
    async def get_exchange_connection_status(self) -> Dict[str, Any]:
        """Get real-time connection status for all exchanges"""
        heartbeat_keys = await self.redis_client.keys("heartbeat:*")
        status = {}
        current_time = time.time()
        
        # Check which exchanges have recent heartbeats
        for key in heartbeat_keys:
            exchange_name = key.split(':')[1]
            data = await self.redis_client.get(key)
            
            if data:
                try:
                    heartbeat_data = json.loads(data)
                    last_heartbeat = heartbeat_data.get('last_heartbeat', 0)
                    seconds_since_heartbeat = current_time - last_heartbeat
                    
                    status[exchange_name] = {
                        'status': 'online',
                        'last_heartbeat': last_heartbeat,
                        'seconds_since_heartbeat': seconds_since_heartbeat,
                        'heartbeat_count': heartbeat_data.get('heartbeat_count', 0),
                        'connection_start': heartbeat_data.get('connection_start', 0)
                    }
                except Exception as e:
                    logger.debug(f"Error parsing heartbeat for {exchange_name}: {e}")
                    status[exchange_name] = {
                        'status': 'unknown',
                        'last_heartbeat': 0,
                        'seconds_since_heartbeat': float('inf'),
                        'heartbeat_count': 0,
                        'connection_start': 0
                    }
            else:
                # Heartbeat key exists but no data (shouldn't happen with TTL)
                status[exchange_name] = {
                    'status': 'offline',
                    'last_heartbeat': 0,
                    'seconds_since_heartbeat': float('inf'),
                    'heartbeat_count': 0,
                    'connection_start': 0
                }
        
        # Check for exchanges that don't have heartbeat keys at all (never connected or long offline)
        # We can infer this from price keys
        price_keys = await self.redis_client.keys("prices:*")
        exchanges_with_prices = set()
        for key in price_keys:
            parts = key.split(':')
            if len(parts) >= 2:
                exchanges_with_prices.add(parts[1])
        
        for exchange in exchanges_with_prices:
            if exchange not in status:
                status[exchange] = {
                    'status': 'offline',
                    'last_heartbeat': 0,
                    'seconds_since_heartbeat': float('inf'),
                    'heartbeat_count': 0,
                    'connection_start': 0
                }
        
        return status
    
    async def get_connection_health_alerts(self) -> List[Dict[str, Any]]:
        """Get alerts based on CONNECTION HEALTH, not price timestamps"""
        alerts = []
        exchange_status = await self.get_exchange_connection_status()
        current_time = time.time()
        
        for exchange, status_info in exchange_status.items():
            status = status_info['status']
            seconds_offline = status_info['seconds_since_heartbeat']
            
            if status == 'offline':
                if seconds_offline <= self.EXCHANGE_OFFLINE_THRESHOLD:
                    # Recently offline - warning
                    alerts.append({
                        'type': 'exchange_recently_offline',
                        'severity': 'warning',
                        'exchange': exchange,
                        'message': f"{exchange} went offline {seconds_offline:.0f} seconds ago (prices still valid)",
                        'seconds_offline': seconds_offline,
                        'prices_still_valid': True
                    })
                elif seconds_offline <= self.PRICE_INVALIDATION_THRESHOLD:
                    # Offline for a while but prices still valid
                    alerts.append({
                        'type': 'exchange_extended_offline',
                        'severity': 'warning',
                        'exchange': exchange,
                        'message': f"{exchange} offline for {seconds_offline:.0f} seconds (prices becoming stale)",
                        'seconds_offline': seconds_offline,
                        'prices_still_valid': True
                    })
                else:
                    # Offline for too long - prices invalid
                    alerts.append({
                        'type': 'exchange_long_offline',
                        'severity': 'critical',
                        'exchange': exchange,
                        'message': f"{exchange} offline for {seconds_offline:.0f} seconds (prices invalidated)",
                        'seconds_offline': seconds_offline,
                        'prices_still_valid': False
                    })
        
        return alerts
    
    async def get_market_health_report(self) -> Dict[str, Any]:
        """Get comprehensive market health report based on connection status"""
        all_prices = await self.get_all_current_prices()
        exchange_status = await self.get_exchange_connection_status()
        
        # Analyze by exchange
        by_exchange = {}
        total_valid = 0
        total_invalid = 0
        
        for key, price_data in all_prices.items():
            exchange = price_data.get('exchange')
            if exchange not in by_exchange:
                by_exchange[exchange] = {
                    'total_pairs': 0,
                    'valid_pairs': 0,
                    'invalid_pairs': 0,
                    'connection_status': exchange_status.get(exchange, {}).get('status', 'unknown'),
                    'seconds_since_heartbeat': exchange_status.get(exchange, {}).get('seconds_since_heartbeat', float('inf')),
                    'oldest_price_age': 0,
                    'newest_price_age': float('inf')
                }
            
            by_exchange[exchange]['total_pairs'] += 1
            
            if price_data.get('is_valid'):
                by_exchange[exchange]['valid_pairs'] += 1
                total_valid += 1
            else:
                by_exchange[exchange]['invalid_pairs'] += 1
                total_invalid += 1
            
            # Track price ages for info
            age = price_data.get('age_seconds', 0)
            if age > by_exchange[exchange]['oldest_price_age']:
                by_exchange[exchange]['oldest_price_age'] = age
            if age < by_exchange[exchange]['newest_price_age']:
                by_exchange[exchange]['newest_price_age'] = age
        
        # Calculate validity ratios
        for exchange_data in by_exchange.values():
            if exchange_data['total_pairs'] > 0:
                exchange_data['validity_ratio'] = exchange_data['valid_pairs'] / exchange_data['total_pairs']
        
        return {
            'timestamp': time.time(),
            'approach': 'connection_health_based',
            'summary': {
                'total_prices': len(all_prices),
                'valid_prices': total_valid,
                'invalid_prices': total_invalid,
                'validity_ratio': total_valid / len(all_prices) if all_prices else 0
            },
            'by_exchange': by_exchange,
            'exchange_status': exchange_status,
            'thresholds': {
                'heartbeat_ttl': self.CONNECTION_HEARTBEAT_TTL,
                'offline_threshold': self.EXCHANGE_OFFLINE_THRESHOLD,
                'invalidation_threshold': self.PRICE_INVALIDATION_THRESHOLD
            }
        }
    
    async def invalidate_exchange_prices(self, exchange: str):
        """Manually invalidate all prices for an exchange (when connection confirmed dead)"""
        try:
            price_keys = await self.redis_client.keys(f"prices:{exchange}:*")
            invalidated_count = 0
            
            for key in price_keys:
                data = await self.redis_client.get(key)
                if data:
                    try:
                        price_data = json.loads(data)
                        price_data['invalidated_at'] = time.time()
                        price_data['invalidation_reason'] = 'manual_exchange_offline'
                        await self.redis_client.set(key, json.dumps(price_data))
                        invalidated_count += 1
                    except Exception as e:
                        logger.debug(f"Error invalidating price {key}: {e}")
            
            logger.info(f"Manually invalidated {invalidated_count} prices for {exchange}")
            return invalidated_count
            
        except Exception as e:
            logger.error(f"Error invalidating prices for {exchange}: {e}")
            return 0
    
    async def cleanup_old_prices(self):
        """Clean up only truly old/invalid prices (very conservative)"""
        current_time = time.time()
        
        # Only clean prices that are:
        # 1. From exchanges offline for more than 1 hour, AND
        # 2. Prices older than 2 hours
        
        price_keys = await self.redis_client.keys("prices:*")
        exchange_status = await self.get_exchange_connection_status()
        cleaned_count = 0
        
        for key in price_keys:
            try:
                data = await self.redis_client.get(key)
                if data:
                    price_data = json.loads(data)
                    exchange = price_data.get('exchange')
                    price_age = current_time - price_data.get('timestamp', current_time)
                    
                    # Get exchange status
                    exchange_info = exchange_status.get(exchange, {})
                    seconds_since_heartbeat = exchange_info.get('seconds_since_heartbeat', 0)
                    
                    # Very conservative cleanup: only remove if exchange offline > 1 hour AND price > 2 hours old
                    if seconds_since_heartbeat > 3600 and price_age > 7200:
                        await self.redis_client.delete(key)
                        cleaned_count += 1
                        logger.debug(f"Cleaned very old price: {key} (exchange offline {seconds_since_heartbeat:.0f}s, price age {price_age:.0f}s)")
            except Exception as e:
                logger.debug(f"Error processing price for cleanup {key}: {e}")
                # Delete corrupted data
                await self.redis_client.delete(key)
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Conservative cleanup: removed {cleaned_count} very old prices")
    
    # Rest of the methods remain the same...
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
        """Clean up old opportunity data only (prices are kept based on connection health)"""
        current_time = time.time()
        
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
        
        # Conservative price cleanup
        await self.cleanup_old_prices()
        
        if old_active_opportunities or cleaned_historical > 0:
            logger.info(
                f"Cleanup completed - "
                f"Active opportunities: {len(old_active_opportunities)}, "
                f"Historical opportunities: {cleaned_historical}"
            )
    
    async def clear_all_data(self):
        """Clear all data (for testing)"""
        # Clear all prices
        price_keys = await self.redis_client.keys("prices:*")
        if price_keys:
            await self.redis_client.delete(*price_keys)
        
        # Clear all opportunities
        opp_keys = await self.redis_client.keys("opportunity:*")
        if opp_keys:
            await self.redis_client.delete(*opp_keys)
        
        # Clear heartbeats
        heartbeat_keys = await self.redis_client.keys("heartbeat:*")
        if heartbeat_keys:
            await self.redis_client.delete(*heartbeat_keys)
        
        await self.redis_client.delete("opportunities:latest")
        
        logger.info("All Redis data cleared")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False

# Global Redis Manager instance
redis_manager = RedisManager()
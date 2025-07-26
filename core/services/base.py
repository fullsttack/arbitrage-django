import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any, Optional
from channels.layers import get_channel_layer
from core.redis_manager import redis_manager

logger = logging.getLogger(__name__)

class BaseExchangeService(ABC):
    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self.is_connected = False
        self.is_receiving_data = False
        self.channel_layer = get_channel_layer()
        
        # Connection health tracking
        self.last_message_time = 0
        self.last_ping_time = 0
        self.last_data_time = 0
        self.connection_start_time = 0
        
        # Enhanced health tracking (NEW)
        self.total_messages_received = 0
        self.total_price_updates_sent = 0
        self.connection_attempts = 0
        self.successful_connections = 0
        self.last_successful_connection = 0
        self.data_gaps = []  # Track periods with no data
        self.current_data_gap_start = 0
        
        # Health check settings - MORE CONSERVATIVE
        self.MESSAGE_TIMEOUT = 300  # 5 minutes for messages (was 3 minutes)
        self.DATA_TIMEOUT = 600     # 10 minutes for data (was 5 minutes)
        self.PING_TIMEOUT = 120     # 2 minutes ping timeout (was 1 minute)
        
        # HEARTBEAT SYSTEM (NEW) - Key to new approach
        self.HEARTBEAT_INTERVAL = 30  # Send heartbeat every 30 seconds
        self.last_heartbeat_sent = 0
        
        # Data quality settings (NEW) - but more relaxed
        self.MAX_DATA_GAP = 300      # 5 minutes without data = concern (was 1 minute)
        self.CRITICAL_DATA_GAP = 900  # 15 minutes without data = critical (was 2 minutes)
        
        # Throttling for broadcasts
        self._last_broadcast_time = {}
        
        # Health status cache (NEW)
        self._health_status_cache = {
            'status': 'initializing',
            'last_update': time.time(),
            'details': {}
        }

    async def init_redis(self):
        """Initialize Redis connection"""
        if not redis_manager.is_connected:
            await redis_manager.connect()

    async def save_price_data(self, symbol: str, bid_price: Decimal, ask_price: Decimal, 
                             bid_volume: Decimal = Decimal('0'), ask_volume: Decimal = Decimal('0')):
        """Save price data and send heartbeat to maintain connection health"""
        await self.init_redis()
        
        current_time = time.time()
        
        # Update data tracking
        self.last_data_time = current_time
        self.is_receiving_data = True
        self.total_price_updates_sent += 1
        
        # Track data gap closure (NEW)
        if self.current_data_gap_start > 0:
            gap_duration = current_time - self.current_data_gap_start
            if gap_duration > self.MAX_DATA_GAP:
                self.data_gaps.append({
                    'start': self.current_data_gap_start,
                    'end': current_time,
                    'duration': gap_duration,
                    'symbol': symbol
                })
                logger.info(
                    f"{self.exchange_name}: Data gap closed for {symbol} "
                    f"(duration: {gap_duration:.1f}s) - this is NORMAL for low-volume periods"
                )
            self.current_data_gap_start = 0
        
        # Save to Redis (NO TTL - let connection health determine validity)
        await redis_manager.save_price_data(
            exchange=self.exchange_name,
            symbol=symbol,
            bid_price=float(bid_price),
            ask_price=float(ask_price),
            bid_volume=float(bid_volume),
            ask_volume=float(ask_volume)
        )
        
        # Update health status cache (NEW)
        await self._update_health_status_cache()
        
        # Throttled broadcast to prevent channel overflow
        if self.channel_layer:
            key = f"{self.exchange_name}_{symbol}"
            
            # Only broadcast if more than 3 seconds has passed since last broadcast for this symbol
            if current_time - self._last_broadcast_time.get(key, 0) > 3:
                price_data = {
                    'exchange': self.exchange_name,
                    'symbol': symbol,
                    'bid_price': float(bid_price),
                    'ask_price': float(ask_price),
                    'bid_volume': float(bid_volume),
                    'ask_volume': float(ask_volume),
                    'timestamp': current_time,
                    # Add health info to broadcast (NEW)
                    'exchange_health': self._health_status_cache['status'],
                    'connection_status': 'online'
                }
                
                try:
                    await self.channel_layer.group_send(
                        'arbitrage_updates',
                        {
                            'type': 'send_price_update',
                            'price_data': price_data
                        }
                    )
                    self._last_broadcast_time[key] = current_time
                except Exception as e:
                    # Channel is full, skip this broadcast and throttle more aggressively
                    logger.debug(f"Skipped broadcast for {key}: {e}")
                    # Increase throttling when channel is full
                    self._last_broadcast_time[key] = current_time + 10  # Skip next 10 seconds
        
        logger.debug(
            f"Saved and broadcast {self.exchange_name} {symbol}: "
            f"bid={bid_price}, ask={ask_price} "
            f"(total updates: {self.total_price_updates_sent})"
        )

    async def send_heartbeat_if_needed(self):
        """Send heartbeat to Redis if no recent price updates (CRITICAL NEW FEATURE)"""
        current_time = time.time()
        
        # Send heartbeat if no recent price updates
        if current_time - self.last_heartbeat_sent >= self.HEARTBEAT_INTERVAL:
            await self.init_redis()
            
            # Send heartbeat even without price data
            await redis_manager._update_connection_heartbeat(self.exchange_name, current_time)
            self.last_heartbeat_sent = current_time
            
            logger.debug(f"{self.exchange_name}: Heartbeat sent (no price updates in {self.HEARTBEAT_INTERVAL}s)")

    async def _update_health_status_cache(self):
        """Update cached health status with comprehensive info (NEW)"""
        current_time = time.time()
        
        # Determine overall status
        status = "healthy"
        details = {}
        
        # Check connection status
        if not self.is_connected:
            status = "disconnected"
        elif not self.is_receiving_data:
            status = "connected_no_data"
        else:
            # Check data freshness - but be MUCH more lenient
            if self.last_data_time > 0:
                time_since_data = current_time - self.last_data_time
                if time_since_data > self.CRITICAL_DATA_GAP:  # 15 minutes
                    status = "critical"
                elif time_since_data > self.MAX_DATA_GAP:  # 5 minutes
                    status = "warning_quiet_market"  # Different status for market quietness
        
        # Calculate uptime and reliability metrics
        connection_uptime = current_time - self.connection_start_time if self.connection_start_time > 0 else 0
        connection_success_rate = (self.successful_connections / max(1, self.connection_attempts)) * 100
        
        # Recent data gaps (last hour) - but don't treat as errors
        recent_gaps = [
            gap for gap in self.data_gaps 
            if current_time - gap['end'] <= 3600  # Last hour
        ]
        
        details = {
            'connection_uptime': connection_uptime,
            'messages_received': self.total_messages_received,
            'price_updates_sent': self.total_price_updates_sent,
            'connection_success_rate': connection_success_rate,
            'last_data_age': current_time - self.last_data_time if self.last_data_time > 0 else float('inf'),
            'recent_quiet_periods': len(recent_gaps),  # Renamed from "data_gaps"
            'total_quiet_time_last_hour': sum(gap['duration'] for gap in recent_gaps),
            'current_quiet_duration': current_time - self.current_data_gap_start if self.current_data_gap_start > 0 else 0,
            'last_heartbeat_sent': self.last_heartbeat_sent
        }
        
        self._health_status_cache = {
            'status': status,
            'last_update': current_time,
            'details': details
        }

    def update_message_time(self):
        """Update last message timestamp with enhanced tracking"""
        current_time = time.time()
        self.last_message_time = current_time
        self.total_messages_received += 1
        
        # Log periodic stats (every 1000 messages)
        if self.total_messages_received % 1000 == 0:
            uptime = current_time - self.connection_start_time if self.connection_start_time > 0 else 0
            msg_rate = self.total_messages_received / max(1, uptime) if uptime > 0 else 0
            logger.debug(
                f"{self.exchange_name}: {self.total_messages_received} messages received "
                f"(rate: {msg_rate:.2f}/s, uptime: {uptime:.0f}s)"
            )
    
    def update_ping_time(self):
        """Update last ping timestamp"""
        self.last_ping_time = time.time()

    def is_connection_healthy(self) -> bool:
        """Check if connection is healthy with MUCH MORE RELAXED thresholds"""
        current_time = time.time()
        
        # Check if we're receiving any messages - faster detection
        if self.last_message_time > 0:
            message_age = current_time - self.last_message_time
            if message_age > 30:  # ULTRA-FAST detection - 30 seconds only
                logger.warning(
                    f"{self.exchange_name}: No messages for {message_age:.1f}s - connection likely dead"
                )
                return False
        
        # Check if we're receiving price data with gap tracking - MUCH MORE RELAXED
        if self.last_data_time > 0:
            data_age = current_time - self.last_data_time
            
            # Start tracking quiet period if not already tracking
            if data_age > self.MAX_DATA_GAP and self.current_data_gap_start == 0:
                self.current_data_gap_start = self.last_data_time
                logger.info(
                    f"{self.exchange_name}: Quiet market period started - no price updates for {data_age:.1f}s "
                    f"(this is NORMAL for low-volume periods)"
                )
            
            # Critical data gap - MUCH more lenient
            if data_age > self.CRITICAL_DATA_GAP:  # 15 minutes now
                logger.error(
                    f"{self.exchange_name}: Extended quiet period - no price updates for {data_age:.1f}s - "
                    f"may indicate connection issues"
                )
                return False
            
            # Warning level data gap - Don't treat as error, just log
            elif data_age > self.DATA_TIMEOUT:  # 10 minutes
                logger.info(
                    f"{self.exchange_name}: Quiet market - no price data for {data_age:.1f}s "
                    f"(normal for low-volume periods)"
                )
                # Don't return False here - this is normal!
        
        return True

    def mark_connection_dead(self, reason: str = "Unknown"):
        """Mark connection as dead and log reason with enhanced tracking"""
        current_time = time.time()
        
        # Track connection failure
        if self.is_connected:
            connection_duration = current_time - self.connection_start_time if self.connection_start_time > 0 else 0
            logger.error(
                f"{self.exchange_name} connection marked as dead: {reason} "
                f"(was connected for {connection_duration:.1f}s, "
                f"sent {self.total_price_updates_sent} price updates)"
            )
        
        self.is_connected = False
        self.is_receiving_data = False
        
        # Update health status
        self._health_status_cache['status'] = 'disconnected'
        self._health_status_cache['last_update'] = current_time
        self._health_status_cache['details']['disconnection_reason'] = reason

    def reset_connection_state(self):
        """Reset all connection tracking with enhanced metrics"""
        current_time = time.time()
        
        # Track connection attempt
        self.connection_attempts += 1
        if self.is_connected:
            self.successful_connections += 1
            self.last_successful_connection = current_time
        
        self.connection_start_time = current_time
        self.last_message_time = current_time
        self.last_ping_time = current_time
        self.last_data_time = 0  # Will be set when first data arrives
        self.is_receiving_data = False
        self.last_heartbeat_sent = current_time  # Start heartbeat tracking
        
        # Reset counters for this session
        self.total_messages_received = 0
        self.total_price_updates_sent = 0
        
        # Clean old data gaps (keep only last 24 hours)
        cutoff_time = current_time - 86400  # 24 hours ago
        self.data_gaps = [gap for gap in self.data_gaps if gap['end'] > cutoff_time]
        self.current_data_gap_start = 0
        
        logger.info(
            f"{self.exchange_name}: Connection state reset "
            f"(attempt {self.connection_attempts}, "
            f"success rate: {(self.successful_connections/max(1,self.connection_attempts))*100:.1f}%)"
        )

    def get_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive health metrics (NEW)"""
        current_time = time.time()
        
        # Calculate additional metrics
        connection_uptime = current_time - self.connection_start_time if self.connection_start_time > 0 else 0
        data_age = current_time - self.last_data_time if self.last_data_time > 0 else float('inf')
        message_age = current_time - self.last_message_time if self.last_message_time > 0 else float('inf')
        heartbeat_age = current_time - self.last_heartbeat_sent if self.last_heartbeat_sent > 0 else float('inf')
        
        # Recent quiet periods (last hour) - reframed positively
        recent_gaps = [
            gap for gap in self.data_gaps 
            if current_time - gap['end'] <= 3600
        ]
        
        return {
            'exchange': self.exchange_name,
            'status': self._health_status_cache['status'],
            'is_connected': self.is_connected,
            'is_receiving_data': self.is_receiving_data,
            'connection_uptime': connection_uptime,
            'data_age_seconds': data_age,
            'message_age_seconds': message_age,
            'heartbeat_age_seconds': heartbeat_age,
            'total_messages': self.total_messages_received,
            'total_price_updates': self.total_price_updates_sent,
            'connection_attempts': self.connection_attempts,
            'successful_connections': self.successful_connections,
            'connection_success_rate': (self.successful_connections / max(1, self.connection_attempts)) * 100,
            'recent_quiet_periods': len(recent_gaps),
            'total_quiet_time_last_hour': sum(gap['duration'] for gap in recent_gaps),
            'current_quiet_duration': current_time - self.current_data_gap_start if self.current_data_gap_start > 0 else 0,
            'last_successful_connection': self.last_successful_connection,
            'health_details': self._health_status_cache['details'],
            'interpretation': 'quiet_periods_are_normal_for_low_volume_markets'
        }

    @abstractmethod
    async def connect(self):
        """Connect to exchange service"""
        pass

    @abstractmethod
    async def subscribe_to_pairs(self, pairs: list):
        """Subscribe to trading pairs"""
        pass

    @abstractmethod
    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse price data from exchange"""
        pass

    async def disconnect(self):
        """Disconnect from exchange service"""
        self.mark_connection_dead("Manual disconnect")
        
    async def health_monitor(self):
        """Monitor connection health continuously with enhanced tracking and HEARTBEAT"""
        while self.is_connected:
            try:
                # Send heartbeat if needed (CRITICAL - keeps connection alive in Redis)
                await self.send_heartbeat_if_needed()
                
                # Check connection health with relaxed thresholds
                if not self.is_connection_healthy():
                    self.mark_connection_dead("Health check failed")
                    break
                
                # Update health status cache
                await self._update_health_status_cache()
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"{self.exchange_name} health monitor error: {e}")
                break
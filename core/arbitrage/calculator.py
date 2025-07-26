import asyncio
import json
import logging
import time
from decimal import Decimal
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from core.redis_manager import redis_manager
from core.models import TradingPair

logger = logging.getLogger(__name__)
performance_logger = logging.getLogger('performance')

@dataclass
class PricePoint:
    exchange: str
    symbol: str
    bid_price: float  # highest buy price
    ask_price: float  # lowest sell price
    bid_volume: float  # buy volume
    ask_volume: float  # sell volume
    timestamp: float
    # Trading pair settings
    arbitrage_threshold: float
    min_volume: float
    max_volume: float
    # Connection-based validity (NEW APPROACH)
    is_valid: bool = True
    validity_reason: str = "unknown"
    exchange_status: str = "unknown"
    price_age_seconds: float = 0

@dataclass
class ArbitrageOpportunity:
    base_currency: str
    quote_currency: str
    buy_exchange: str  # exchange where we buy
    sell_exchange: str  # exchange where we sell
    buy_price: float  # buy price (ask price)
    sell_price: float  # sell price (bid price)
    buy_volume: float  # available buy volume (ask volume on buy exchange)
    sell_volume: float  # available sell volume (bid volume on sell exchange)
    trade_volume: float  # actual tradeable volume (minimum of buy/sell)
    profit_amount: float
    profit_percentage: float
    timestamp: float
    # Connection-based quality (CORRECTED APPROACH)
    data_quality: str = "unknown"  # valid, invalid, mixed
    connection_health: str = "unknown"  # all_online, some_offline, mixed

class FastArbitrageCalculator:
    def __init__(self):
        self.is_running = False
        self.channel_layer = get_channel_layer()
        self.trading_pairs_cache = {}
        self.last_cache_update = 0
        self.calculation_count = 0
        self.last_opportunities_count = 0
        
        # Performance optimization settings
        self.CACHE_UPDATE_INTERVAL = 30  # Update cache every 30 seconds
        self.CALCULATION_INTERVAL = 0.15  # Faster calculation interval (150ms)
        self.MIN_CALCULATION_INTERVAL = 0.05  # Minimum interval (50ms)
        self.SIGNIFICANT_PROFIT_THRESHOLD = 0.01  # Broadcast threshold - should match DB threshold
        
        # NEW APPROACH: Connection-based validity instead of time-based
        self.MIN_EXCHANGES_FOR_ARBITRAGE = 2  # Need at least 2 exchanges with valid connections
        self.QUALITY_CHECK_INTERVAL = 10  # Check data quality every 10 calculations
        
        # Statistics
        self.stats = {
            'total_calculations': 0,
            'valid_opportunities': 0,
            'invalid_opportunities_rejected': 0,
            'mixed_connection_opportunities': 0,
            'last_quality_check': 0
        }
        
    async def start_calculation(self):
        """Start arbitrage calculation loop with connection-based validity"""
        self.is_running = True
        logger.info("FastArbitrageCalculator started with connection-based validity approach")
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Update trading pairs cache periodically
                if start_time - self.last_cache_update > self.CACHE_UPDATE_INTERVAL:
                    await self._update_trading_pairs_cache()
                    self.last_cache_update = start_time
                
                # Periodic connection health check
                if self.calculation_count % self.QUALITY_CHECK_INTERVAL == 0:
                    # await self._log_connection_health_status()  # Commented out to reduce spam
                    self.stats['last_quality_check'] = start_time
                
                # Find arbitrage opportunities with connection-based validation
                opportunities = await self._find_arbitrage_opportunities_connection_based()
                
                if opportunities:
                    # Separate opportunities by connection health
                    valid_opportunities = []
                    mixed_opportunities = []
                    
                    for opp in opportunities:
                        if opp.data_quality == "valid":
                            valid_opportunities.append(opp)
                        elif opp.data_quality == "mixed":
                            mixed_opportunities.append(opp)
                        # Skip "invalid" opportunities completely
                    
                    # Save all valid opportunities (valid + mixed)
                    all_valid_opportunities = valid_opportunities + mixed_opportunities
                    if all_valid_opportunities:
                        await self._save_opportunities(all_valid_opportunities)
                    
                    # Broadcast based on connection health
                    significant_opportunities = []
                    for opp in valid_opportunities:  # Only broadcast fully valid opportunities
                        # Get minimum threshold for this currency pair from trading pairs cache
                        base_quote = f"{opp.base_currency}_{opp.quote_currency}"
                        min_threshold_for_pair = float('inf')
                        
                        if base_quote in self.trading_pairs_cache:
                            for pair_info in self.trading_pairs_cache[base_quote]:
                                if (pair_info['exchange'] == opp.buy_exchange or 
                                    pair_info['exchange'] == opp.sell_exchange):
                                    min_threshold_for_pair = min(min_threshold_for_pair, pair_info['arbitrage_threshold'])
                        
                        # Use database threshold instead of hard-coded one
                        if min_threshold_for_pair != float('inf') and opp.profit_percentage > min_threshold_for_pair:
                            significant_opportunities.append(opp)
                        elif min_threshold_for_pair == float('inf') and opp.profit_percentage > self.SIGNIFICANT_PROFIT_THRESHOLD:
                            # Fallback to hard-coded threshold if no DB threshold found
                            significant_opportunities.append(opp)
                    
                    if significant_opportunities:
                        await self._broadcast_opportunities(significant_opportunities)
                    
                    # Update statistics
                    self.stats['valid_opportunities'] += len(valid_opportunities)
                    self.stats['mixed_connection_opportunities'] += len(mixed_opportunities)
                    
                    # Log performance metrics with connection health info
                    if len(all_valid_opportunities) != self.last_opportunities_count:
                        performance_logger.info(
                            f"Arbitrage: Found {len(all_valid_opportunities)} opportunities "
                            f"({len(valid_opportunities)} fully valid, {len(mixed_opportunities)} mixed connection, "
                            f"{len(significant_opportunities)} broadcast-worthy) - "
                            f"Rejected: {self.stats['invalid_opportunities_rejected']} invalid"
                        )
                        self.last_opportunities_count = len(all_valid_opportunities)
                
                # Calculate processing time and adjust interval
                processing_time = time.time() - start_time
                
                # Dynamic interval adjustment based on processing time
                if processing_time > self.CALCULATION_INTERVAL:
                    sleep_time = self.MIN_CALCULATION_INTERVAL
                    if self.calculation_count % 100 == 0:  # Log every 100 calculations
                        logger.warning(f"Arbitrage calculation taking {processing_time:.3f}s, reducing interval")
                else:
                    sleep_time = max(self.MIN_CALCULATION_INTERVAL, self.CALCULATION_INTERVAL - processing_time)
                
                self.calculation_count += 1
                self.stats['total_calculations'] += 1
                
                # Performance logging every 1000 calculations
                if self.calculation_count % 1000 == 0:
                    performance_logger.debug(
                        f"Arbitrage: {self.calculation_count} calculations, "
                        f"avg time: {processing_time:.3f}s, "
                        f"validity ratio: {self.stats['valid_opportunities']/(self.stats['valid_opportunities']+self.stats['invalid_opportunities_rejected']+1):.2f}"
                    )
                
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in arbitrage calculation: {e}")
                await asyncio.sleep(1)  # Wait longer on error

    async def _log_connection_health_status(self):
        """Log current connection health status"""
        try:
            health_report = await redis_manager.get_market_health_report()
            
            summary = health_report.get('summary', {})
            by_exchange = health_report.get('by_exchange', {})
            
            performance_logger.info(
                f"Connection Health Status - "
                f"Total prices: {summary.get('total_prices', 0)}, "
                f"Valid: {summary.get('valid_prices', 0)}, "
                f"Invalid: {summary.get('invalid_prices', 0)}, "
                f"Validity ratio: {summary.get('validity_ratio', 0):.2f}"
            )
            
            # Log per-exchange status
            for exchange, data in by_exchange.items():
                if data['total_pairs'] > 0:
                    logger.debug(
                        f"{exchange}: {data['valid_pairs']}/{data['total_pairs']} valid "
                        f"(status: {data['connection_status']}, "
                        f"heartbeat: {data.get('seconds_since_heartbeat', 'N/A')}s ago)"
                    )
            
        except Exception as e:
            logger.error(f"Error logging connection health status: {e}")

    @database_sync_to_async
    def _update_trading_pairs_cache_sync(self):
        """Update trading pairs cache from database (sync version)"""
        try:
            # Get active trading pairs
            pairs = TradingPair.objects.filter(
                is_active=True,
                exchange__is_active=True
            ).select_related('exchange', 'base_currency', 'quote_currency')
            
            trading_pairs_cache = {}
            
            for pair in pairs:
                key = f"{pair.base_currency.symbol}_{pair.quote_currency.symbol}"
                if key not in trading_pairs_cache:
                    trading_pairs_cache[key] = []
                
                trading_pairs_cache[key].append({
                    'exchange': pair.exchange.name,
                    'symbol': pair.arbitrage_symbol,  # Use consistent symbol for matching
                    'arbitrage_threshold': float(pair.arbitrage_threshold),
                    'min_volume': float(pair.min_volume),
                    'max_volume': float(pair.max_volume)
                })
            
            logger.debug(f"Updated trading pairs cache: {len(trading_pairs_cache)} currency pairs")
            return trading_pairs_cache
            
        except Exception as e:
            logger.error(f"Error updating trading pairs cache: {e}")
            return {}
            
    async def _update_trading_pairs_cache(self):
        """Update trading pairs cache from database"""
        self.trading_pairs_cache = await self._update_trading_pairs_cache_sync()

    async def _find_arbitrage_opportunities_connection_based(self) -> List[ArbitrageOpportunity]:
        """Find arbitrage opportunities with CONNECTION-BASED validation (CORRECTED APPROACH)"""
        opportunities = []
        
        try:
            # Get valid prices (based on connection health, not timestamp)
            valid_prices = await redis_manager.get_valid_prices_only()
            
            # Also get all prices for mixed scenarios
            all_prices = await redis_manager.get_all_current_prices()
            
            if not valid_prices and not all_prices:
                return opportunities
            
            # Group prices by currency pair
            valid_price_groups = self._group_prices_by_pair_optimized(valid_prices)
            all_price_groups = self._group_prices_by_pair_optimized(all_prices)
            
            # Check each currency pair for arbitrage opportunities
            for currency_pair in set(valid_price_groups.keys()) | set(all_price_groups.keys()):
                valid_prices_for_pair = valid_price_groups.get(currency_pair, [])
                all_prices_for_pair = all_price_groups.get(currency_pair, [])
                
                # Strategy 1: Try with valid connections only (preferred)
                if len(valid_prices_for_pair) >= self.MIN_EXCHANGES_FOR_ARBITRAGE:
                    valid_opportunities = await self._check_pair_arbitrage_with_connection_health(
                        currency_pair, valid_prices_for_pair, "valid"
                    )
                    opportunities.extend(valid_opportunities)
                
                # Strategy 2: Try with mixed connection health if not enough valid
                elif len(all_prices_for_pair) >= self.MIN_EXCHANGES_FOR_ARBITRAGE:
                    # Filter to only include recent offline exchanges (not long offline)
                    acceptable_prices = []
                    for price in all_prices_for_pair:
                        validity_reason = getattr(price, 'validity_reason', '')
                        if price.is_valid or validity_reason.startswith('recent_offline'):
                            acceptable_prices.append(price)
                    
                    if len(acceptable_prices) >= self.MIN_EXCHANGES_FOR_ARBITRAGE:
                        mixed_opportunities = await self._check_pair_arbitrage_with_connection_health(
                            currency_pair, acceptable_prices, "mixed"
                        )
                        opportunities.extend(mixed_opportunities)
                    else:
                        logger.debug(
                            f"Skipping {currency_pair}: insufficient acceptable connections "
                            f"(acceptable: {len(acceptable_prices)}, required: {self.MIN_EXCHANGES_FOR_ARBITRAGE})"
                        )
                        self.stats['invalid_opportunities_rejected'] += 1
                
                # Strategy 3: Log when we skip due to insufficient data
                else:
                    logger.debug(
                        f"Skipping {currency_pair}: insufficient connections "
                        f"(valid: {len(valid_prices_for_pair)}, all: {len(all_prices_for_pair)})"
                    )
            
        except Exception as e:
            logger.error(f"Error finding arbitrage opportunities with connection-based validation: {e}")
        
        return opportunities

    async def _check_pair_arbitrage_with_connection_health(self, currency_pair: str, prices: List[PricePoint], 
                                                          quality_level: str) -> List[ArbitrageOpportunity]:
        """Arbitrage checking with connection health assessment"""
        opportunities = []
        
        try:
            base_currency, quote_currency = currency_pair.split('_', 1)
            
            # Assess overall connection health for this pair
            online_exchanges = sum(1 for price in prices if price.exchange_status == 'online')
            total_exchanges = len(prices)
            
            # Determine connection health
            if online_exchanges == total_exchanges:
                connection_health = "all_online"
            elif online_exchanges >= total_exchanges * 0.5:  # At least 50% online
                connection_health = "mostly_online"
            else:
                connection_health = "mostly_offline"
            
            num_exchanges = len(prices)
            
            # For small number of exchanges, use simple nested loop
            for i in range(num_exchanges):
                price1 = prices[i]
                for j in range(i + 1, num_exchanges):
                    price2 = prices[j]
                    
                    # Check both directions efficiently
                    # Direction 1: buy at price2, sell at price1
                    if price1.bid_price > price2.ask_price:
                        opportunity = self._calculate_opportunity_with_connection_health(
                            base_currency, quote_currency,
                            price2, price1,  # buy_settings, sell_settings
                            price2.ask_price, price1.bid_price,  # buy_price, sell_price
                            quality_level, connection_health
                        )
                        if opportunity:
                            opportunities.append(opportunity)
                    
                    # Direction 2: buy at price1, sell at price2
                    if price2.bid_price > price1.ask_price:
                        opportunity = self._calculate_opportunity_with_connection_health(
                            base_currency, quote_currency,
                            price1, price2,  # buy_settings, sell_settings
                            price1.ask_price, price2.bid_price,  # buy_price, sell_price
                            quality_level, connection_health
                        )
                        if opportunity:
                            opportunities.append(opportunity)
            
        except Exception as e:
            logger.error(f"Error checking arbitrage with connection health for {currency_pair}: {e}")
        
        return opportunities

    def _calculate_opportunity_with_connection_health(self, base_currency: str, quote_currency: str,
                                  buy_settings: PricePoint, sell_settings: PricePoint,
                                  buy_price: float, sell_price: float, 
                                  quality_level: str, connection_health: str) -> Optional[ArbitrageOpportunity]:
        """Calculate opportunity with connection health awareness"""
        try:
            # Quick profit check first (most opportunities will fail this)
            if sell_price <= buy_price:
                return None
            
            # Calculate profit percentage
            profit_percentage = ((sell_price - buy_price) / buy_price) * 100
            
            # Use minimum threshold from both exchanges
            min_threshold = min(buy_settings.arbitrage_threshold, sell_settings.arbitrage_threshold)
            
            # Apply connection health adjustments
            if quality_level == "mixed" and connection_health == "mostly_offline":
                # Require higher profit for mixed quality with poor connections
                adjusted_threshold = min_threshold * 1.3  # 30% higher threshold
            elif quality_level == "mixed":
                # Slightly higher threshold for mixed quality
                adjusted_threshold = min_threshold * 1.1  # 10% higher threshold
            else:
                adjusted_threshold = min_threshold
            
            # Quick threshold check
            if profit_percentage < adjusted_threshold:
                return None
            
            # Check connection health of both exchanges
            if not buy_settings.is_valid and not sell_settings.is_valid:
                # Both exchanges have connection issues - skip
                return None
            
            # Calculate volume constraints (only if profitable)
            min_volume = max(buy_settings.min_volume, sell_settings.min_volume)
            max_volume = min(buy_settings.max_volume, sell_settings.max_volume)
            
            # Available volumes for buy and sell
            buy_available_volume = buy_settings.ask_volume  # volume available for buying
            sell_available_volume = sell_settings.bid_volume  # volume available for selling
            
            # Actual tradeable volume is the minimum
            trade_volume = min(buy_available_volume, sell_available_volume, max_volume)
            
            # Volume constraint check
            if trade_volume < min_volume:
                return None
            
            # Calculate profit amount
            profit_amount = (sell_price - buy_price) * trade_volume
            
            return ArbitrageOpportunity(
                base_currency=base_currency,
                quote_currency=quote_currency,
                buy_exchange=buy_settings.exchange,
                sell_exchange=sell_settings.exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                buy_volume=buy_available_volume,
                sell_volume=sell_available_volume,
                trade_volume=trade_volume,
                profit_amount=profit_amount,
                profit_percentage=profit_percentage,
                timestamp=time.time(),
                data_quality=quality_level,
                connection_health=connection_health
            )
            
        except Exception as e:
            logger.debug(f"Error calculating opportunity with connection health: {e}")
            return None

    def _group_prices_by_pair_optimized(self, all_prices: Dict[str, Any]) -> Dict[str, List[PricePoint]]:
        """Optimized version of price grouping with connection-based validity"""
        price_groups = {}
        
        # Pre-build lookup for trading pairs to avoid repeated dictionary lookups
        exchange_symbol_to_pair = {}
        for currency_pair, pairs in self.trading_pairs_cache.items():
            for pair in pairs:
                key = f"{pair['exchange']}:{pair['symbol']}"
                exchange_symbol_to_pair[key] = (currency_pair, pair)
        
        for redis_key, price_data in all_prices.items():
            try:
                # Extract exchange and symbol from key: "prices:exchange:symbol"
                parts = redis_key.split(':', 2)  # Limit splits for performance
                if len(parts) < 3:
                    continue
                    
                exchange = parts[1]
                symbol = parts[2]
                lookup_key = f"{exchange}:{symbol}"
                
                # Fast lookup using pre-built dictionary
                if lookup_key not in exchange_symbol_to_pair:
                    continue
                
                currency_pair, trading_pair_info = exchange_symbol_to_pair[lookup_key]
                
                # Create PricePoint with connection-based validity
                price_point = PricePoint(
                    exchange=exchange,
                    symbol=symbol,
                    bid_price=price_data['bid_price'],
                    ask_price=price_data['ask_price'],
                    bid_volume=price_data.get('bid_volume', 0),
                    ask_volume=price_data.get('ask_volume', 0),
                    timestamp=price_data['timestamp'],
                    arbitrage_threshold=trading_pair_info['arbitrage_threshold'],
                    min_volume=trading_pair_info['min_volume'],
                    max_volume=trading_pair_info['max_volume'],
                    is_valid=price_data.get('is_valid', False),
                    validity_reason=price_data.get('validity_reason', 'unknown'),
                    exchange_status=price_data.get('exchange_status', 'unknown'),
                    price_age_seconds=price_data.get('age_seconds', 0)
                )
                
                if currency_pair not in price_groups:
                    price_groups[currency_pair] = []
                
                price_groups[currency_pair].append(price_point)
                
            except Exception as e:
                logger.debug(f"Error processing price data for {redis_key}: {e}")
                continue
        
        return price_groups

    async def _save_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """Save opportunities to Redis with connection health info"""
        try:
            save_tasks = []
            for opp in opportunities:
                opportunity_data = {
                    'base_currency': opp.base_currency,
                    'quote_currency': opp.quote_currency,
                    'symbol': f"{opp.base_currency}/{opp.quote_currency}",
                    'buy_exchange': opp.buy_exchange,
                    'sell_exchange': opp.sell_exchange,
                    'buy_price': opp.buy_price,
                    'sell_price': opp.sell_price,
                    'buy_volume': opp.buy_volume,
                    'sell_volume': opp.sell_volume,
                    'trade_volume': opp.trade_volume,
                    'profit_amount': opp.profit_amount,
                    'profit_percentage': round(opp.profit_percentage, 2),
                    'timestamp': opp.timestamp,
                    'data_quality': opp.data_quality,
                    'connection_health': opp.connection_health
                }
                
                save_tasks.append(redis_manager.save_arbitrage_opportunity(opportunity_data))
            
            # Execute all saves concurrently
            if save_tasks:
                await asyncio.gather(*save_tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"Error saving opportunities: {e}")

    async def _broadcast_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """Broadcast opportunities to WebSocket with connection health info"""
        if not self.channel_layer:
            return
            
        try:
            opportunities_data = []
            for opp in opportunities:
                opportunities_data.append({
                    'symbol': f"{opp.base_currency}/{opp.quote_currency}",
                    'buy_exchange': opp.buy_exchange,
                    'sell_exchange': opp.sell_exchange,
                    'profit_percentage': round(opp.profit_percentage, 2),
                    'profit_amount': round(opp.profit_amount, 4),
                    'buy_price': opp.buy_price,
                    'sell_price': opp.sell_price,
                    'buy_volume': opp.buy_volume,
                    'sell_volume': opp.sell_volume,
                    'trade_volume': opp.trade_volume,
                    'timestamp': opp.timestamp,
                    'data_quality': opp.data_quality,
                    'connection_health': opp.connection_health
                })
            
            await self.channel_layer.group_send(
                'arbitrage_updates',
                {
                    'type': 'send_opportunities',
                    'opportunities': opportunities_data
                }
            )
            
        except Exception as e:
            # Don't let broadcast errors stop the calculation
            logger.debug(f"Broadcast error (non-critical): {e}")

    async def stop_calculation(self):
        """Stop arbitrage calculation"""
        self.is_running = False
        
        # Log final statistics
        performance_logger.info(
            f"FastArbitrageCalculator stopped after {self.calculation_count} calculations. "
            f"Stats: {self.stats['valid_opportunities']} valid opportunities, "
            f"{self.stats['invalid_opportunities_rejected']} invalid rejected, "
            f"{self.stats['mixed_connection_opportunities']} mixed connection"
        )
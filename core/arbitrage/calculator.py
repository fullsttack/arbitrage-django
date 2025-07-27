import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from core.redis import redis_manager
from core.models import TradingPair
from ..config_manager import get_arbitrage_config

logger = logging.getLogger(__name__)

@dataclass
class ArbitrageOpportunity:
    """🎯 Simple arbitrage opportunity"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    profit_percentage: float
    profit_amount: float
    volume: float
    buy_volume: float
    sell_volume: float
    timestamp: float

class FastArbitrageCalculator:
    """🚀 Simple and Fast Arbitrage Calculator"""
    
    def __init__(self, config_profile: str = 'default'):
        self.config = get_arbitrage_config(config_profile)
        self.is_running = False
        self.channel_layer = get_channel_layer()
        
        # Simple cache
        self.trading_pairs = {}
        self.last_cache_update = 0
        self.calculation_count = 0
        
        logger.info(f"✅ Arbitrage Calculator initialized with {config_profile} profile")

    async def start_calculation(self):
        """🚀 Start arbitrage calculation loop"""
        self.is_running = True
        logger.info("🚀 Fast arbitrage calculator started")
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Update cache periodically
                if start_time - self.last_cache_update > self.config['cache_update_interval']:
                    await self._update_cache()
                    self.last_cache_update = start_time
                
                # Find opportunities
                opportunities = await self._find_opportunities()
                
                if opportunities:
                    # Save and broadcast significant opportunities
                    await self._process_opportunities(opportunities)
                
                # Dynamic sleep calculation
                processing_time = time.time() - start_time
                sleep_time = max(
                    self.config['min_calculation_interval'], 
                    self.config['calculation_interval'] - processing_time
                )
                
                self.calculation_count += 1
                
                # Log periodically
                if self.calculation_count % self.config['log_interval'] == 0:
                    logger.debug(f"📊 Calculation #{self.calculation_count}, "
                               f"found {len(opportunities)} opportunities, "
                               f"processing time: {processing_time:.3f}s")
                
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"❌ Arbitrage calculation error: {e}")
                await asyncio.sleep(1)

    async def _update_cache(self):
        """📋 Update trading pairs cache"""
        try:
            self.trading_pairs = await self._get_trading_pairs()
            logger.debug(f"📋 Updated cache: {len(self.trading_pairs)} trading pairs")
        except Exception as e:
            logger.error(f"❌ Cache update error: {e}")

    @database_sync_to_async
    def _get_trading_pairs(self) -> Dict[str, Dict]:
        """📋 Get trading pairs from database"""
        pairs = {}
        try:
            active_pairs = TradingPair.objects.filter(
                is_active=True,
                exchange__is_active=True
            ).select_related('exchange', 'base_currency', 'quote_currency')
            
            for pair in active_pairs:
                symbol = f"{pair.base_currency.symbol}/{pair.quote_currency.symbol}"
                exchange = pair.exchange.name
                
                if symbol not in pairs:
                    pairs[symbol] = {}
                
                pairs[symbol][exchange] = {
                    'arbitrage_symbol': pair.arbitrage_symbol,
                    'threshold': float(pair.arbitrage_threshold),
                    'min_volume': float(pair.min_volume),
                    'max_volume': float(pair.max_volume)
                }
            
            return pairs
            
        except Exception as e:
            logger.error(f"❌ Error getting trading pairs: {e}")
            return {}

    async def _find_opportunities(self) -> List[ArbitrageOpportunity]:
        """🎯 Find arbitrage opportunities"""
        opportunities = []
        
        try:
            # Get current prices
            prices = await redis_manager.get_valid_prices()
            if not prices:
                return opportunities
            
            # Group prices by symbol
            price_groups = self._group_prices(prices)
            
            # Check each symbol for arbitrage
            for symbol, exchange_prices in price_groups.items():
                if len(exchange_prices) < self.config['min_exchanges']:
                    continue
                
                symbol_opportunities = self._check_symbol_arbitrage(symbol, exchange_prices)
                opportunities.extend(symbol_opportunities)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"❌ Error finding opportunities: {e}")
            return []

    def _group_prices(self, prices: Dict[str, Any]) -> Dict[str, Dict[str, Dict]]:
        """📊 Group prices by symbol"""
        price_groups = {}
        
        for price_key, price_data in prices.items():
            try:
                # Extract exchange and symbol from Redis key: "price:exchange:symbol"
                parts = price_key.split(':')
                if len(parts) < 3:
                    continue
                    
                exchange = parts[1]
                symbol_key = parts[2]
                
                # Find matching symbol in trading pairs
                symbol = None
                for trading_symbol, exchanges in self.trading_pairs.items():
                    if exchange in exchanges and exchanges[exchange]['arbitrage_symbol'] == symbol_key:
                        symbol = trading_symbol
                        break
                
                if not symbol:
                    continue
                
                if symbol not in price_groups:
                    price_groups[symbol] = {}
                
                price_groups[symbol][exchange] = {
                    'bid_price': price_data['bid_price'],
                    'ask_price': price_data['ask_price'],
                    'bid_volume': price_data.get('bid_volume', 0),
                    'ask_volume': price_data.get('ask_volume', 0),
                    'timestamp': price_data['timestamp']
                }
                
            except Exception as e:
                continue
        
        return price_groups

    def _check_symbol_arbitrage(self, symbol: str, exchange_prices: Dict[str, Dict]) -> List[ArbitrageOpportunity]:
        """🎯 Check arbitrage for a specific symbol"""
        opportunities = []
        
        if symbol not in self.trading_pairs:
            return opportunities
        
        trading_pair_info = self.trading_pairs[symbol]
        exchanges = list(exchange_prices.keys())
        
        # Check all exchange pairs
        for i in range(len(exchanges)):
            for j in range(i + 1, len(exchanges)):
                exchange1 = exchanges[i]
                exchange2 = exchanges[j]
                
                # Skip if either exchange not in trading pairs
                if exchange1 not in trading_pair_info or exchange2 not in trading_pair_info:
                    continue
                
                price1 = exchange_prices[exchange1]
                price2 = exchange_prices[exchange2]
                
                # Check both directions
                # Direction 1: buy on exchange1, sell on exchange2
                opp1 = self._calculate_opportunity(
                    symbol, exchange1, exchange2, 
                    price1['ask_price'], price2['bid_price'],
                    price1['ask_volume'], price2['bid_volume'],
                    trading_pair_info[exchange1], trading_pair_info[exchange2]
                )
                if opp1:
                    opportunities.append(opp1)
                
                # Direction 2: buy on exchange2, sell on exchange1
                opp2 = self._calculate_opportunity(
                    symbol, exchange2, exchange1,
                    price2['ask_price'], price1['bid_price'],
                    price2['ask_volume'], price1['bid_volume'],
                    trading_pair_info[exchange2], trading_pair_info[exchange1]
                )
                if opp2:
                    opportunities.append(opp2)
        
        return opportunities

    def _calculate_opportunity(self, symbol: str, buy_exchange: str, sell_exchange: str,
                             buy_price: float, sell_price: float, 
                             buy_volume: float, sell_volume: float,
                             buy_config: Dict, sell_config: Dict) -> Optional[ArbitrageOpportunity]:
        """💰 Calculate arbitrage opportunity"""
        try:
            # Quick profit check
            if sell_price <= buy_price:
                return None
            
            # Calculate profit percentage
            profit_percentage = ((sell_price - buy_price) / buy_price) * 100
            
            # Check minimum threshold
            min_threshold = min(buy_config['threshold'], sell_config['threshold'])
            if profit_percentage < min_threshold:
                return None
            
            # Calculate tradeable volume
            min_volume = max(buy_config['min_volume'], sell_config['min_volume'])
            max_volume = min(buy_config['max_volume'], sell_config['max_volume'])
            trade_volume = min(buy_volume, sell_volume, max_volume)
            
            if trade_volume < min_volume:
                return None
            
            # Calculate profit amount
            profit_amount = (sell_price - buy_price) * trade_volume
            
            return ArbitrageOpportunity(
                symbol=symbol,
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                profit_percentage=round(profit_percentage, 2),
                profit_amount=round(profit_amount, 4),
                volume=trade_volume,
                buy_volume=buy_volume,
                sell_volume=sell_volume,
                timestamp=time.time()
            )
            
        except Exception as e:
            return None

    async def _process_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """📤 Process opportunities - save and broadcast"""
        try:
            # Filter significant opportunities for broadcasting
            significant_opportunities = [
                opp for opp in opportunities 
                if opp.profit_percentage > self.config['profit_threshold']
            ]
            
            # Save all opportunities
            if opportunities:
                await self._save_opportunities(opportunities)
            
            # Broadcast significant ones
            if significant_opportunities:
                await self._broadcast_opportunities(significant_opportunities)
                logger.debug(f"📡 Broadcast {len(significant_opportunities)} significant opportunities")
            
        except Exception as e:
            logger.error(f"❌ Error processing opportunities: {e}")

    async def _save_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """💾 Save opportunities to Redis"""
        try:
            tasks = []
            for opp in opportunities:
                opportunity_data = {
                    'symbol': opp.symbol,
                    'buy_exchange': opp.buy_exchange,
                    'sell_exchange': opp.sell_exchange,
                    'buy_price': opp.buy_price,
                    'sell_price': opp.sell_price,
                    'profit_percentage': opp.profit_percentage,
                    'profit_amount': opp.profit_amount,
                    'trade_volume': opp.volume,
                    'buy_volume': opp.buy_volume,
                    'sell_volume': opp.sell_volume,
                    'timestamp': opp.timestamp
                }
                tasks.append(redis_manager.save_arbitrage_opportunity(opportunity_data))
            
            # Save in batches
            batch_size = self.config['batch_size']
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i+batch_size]
                await asyncio.gather(*batch, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"❌ Error saving opportunities: {e}")

    async def _broadcast_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """📡 Broadcast opportunities to WebSocket"""
        if not self.channel_layer:
            return
        
        try:
            opportunities_data = []
            for opp in opportunities:
                opportunities_data.append({
                    'symbol': opp.symbol,
                    'buy_exchange': opp.buy_exchange,
                    'sell_exchange': opp.sell_exchange,
                    'profit_percentage': opp.profit_percentage,
                    'profit_amount': opp.profit_amount,
                    'buy_price': opp.buy_price,
                    'sell_price': opp.sell_price,
                    'volume': opp.volume,
                    'buy_volume': opp.buy_volume,
                    'sell_volume': opp.sell_volume,
                    'timestamp': opp.timestamp
                })
            
            await self.channel_layer.group_send(
                'arbitrage_updates',
                {
                    'type': 'send_opportunities',
                    'opportunities': opportunities_data
                }
            )
            
        except Exception as e:
            pass  # Don't let broadcast errors stop calculation

    async def stop_calculation(self):
        """🛑 Stop arbitrage calculation"""
        self.is_running = False
        logger.info(f"🛑 Arbitrage calculator stopped after {self.calculation_count} calculations")

# Legacy compatibility - already defined above
DefaultCalculator = FastArbitrageCalculator
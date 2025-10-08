"""
GRVT Volume Generator Bot - Fully Configurable via .env
Target: Customizable volume in configurable timeframe
Strategy: Ultra-tight spread with all parameters in .env file
Features: Zero gas fees (ZKSync), High-frequency execution, Real-time monitoring
"""
import asyncio
import os
import signal
from datetime import datetime, timedelta
from decimal import Decimal
from dotenv import load_dotenv
from pysdk.grvt_ccxt_pro import GrvtCcxtPro
from pysdk.grvt_ccxt_env import GrvtEnv
import time
import requests

load_dotenv()

class GRVTVolumeBot:
    def __init__(self):
        # ===== API Configuration =====
        self.api_key = os.getenv('GRVT_API_KEY')
        self.sub_account_id = os.getenv('GRVT_SUB_ACCOUNT_ID')
        self.environment = os.getenv('ENVIRONMENT', 'TESTNET').upper()
        
        # ===== Market & Trading Settings =====
        self.market = os.getenv('MARKET', 'BTC_USDT_Perp')
        self.leverage = int(os.getenv('LEVERAGE', 10))
        self.investment = float(os.getenv('INVESTMENT_USDC', 10))
        
        # ===== Volume Target Settings =====
        self.target_volume = float(os.getenv('TARGET_VOLUME', 100000))
        self.max_loss = float(os.getenv('MAX_LOSS', 10))
        self.target_hours = int(os.getenv('TARGET_HOURS', 24))
        
        # ===== Strategy Parameters =====
        self.spread_bps = float(os.getenv('SPREAD_BPS', 2))
        self.orders_per_side = int(os.getenv('ORDERS_PER_SIDE', 10))
        self.order_size_percent = float(os.getenv('ORDER_SIZE_PERCENT', 0.1))
        self.refresh_interval = float(os.getenv('REFRESH_INTERVAL', 2.0))
        
        # ===== Rate Limit Protection =====
        self.delay_between_orders = float(os.getenv('DELAY_BETWEEN_ORDERS', 0.05))
        self.delay_after_cancel = float(os.getenv('DELAY_AFTER_CANCEL', 0.3))
        self.status_interval = int(os.getenv('STATUS_INTERVAL', 30))
        self.max_orders_to_place = int(os.getenv('MAX_ORDERS_TO_PLACE', 10))
        
        # ===== Advanced Settings =====
        self.use_post_only = os.getenv('USE_POST_ONLY', 'true').lower() == 'true'
        self.trading_fee_percent = float(os.getenv('TRADING_FEE_PERCENT', 0.0))
        
        # Calculate derived metrics
        self.hourly_target = self.target_volume / self.target_hours
        self.trades_needed = int(self.target_volume / 10)
        self.avg_trade_size = self.target_volume / self.trades_needed
        
        # GRVT client
        self.client = None
        self.client_order_id = int(time.time() * 1000)
        
        # Tracking
        self.running = True
        self.active_orders = {}
        self.total_volume = 0.0
        self.total_trades = 0
        self.total_fees = 0.0
        self.session_start = None
        self.last_fill_time = time.time()
        
        # Hourly tracking
        self.current_hour_volume = 0.0
        self.current_hour_trades = 0
        self.hour_start = None
        self.hourly_stats = []
        
        # Market info cache
        self.market_info = None
        self.tick_size = None
        self.min_size = None

    async def init(self):
        """Initialize GRVT client"""
        # Set environment
        if self.environment == 'TESTNET':
            env = GrvtEnv.TESTNET
        elif self.environment == 'PROD':
            env = GrvtEnv.PROD
        else:
            env = GrvtEnv.DEV
        
        # Initialize GRVT CCXT client
        self.client = GrvtCcxtPro(env=env)
        
        # Authenticate
        try:
            await self.client.login_with_api_key(
                api_key=self.api_key,
                trading_account_id=self.sub_account_id
            )
            print(f"✅ Authenticated to GRVT")
        except Exception as e:
            raise Exception(f"Authentication failed: {e}")
        
        self.session_start = datetime.now()
        self.hour_start = datetime.now()
        
        # Fetch market info
        await self.fetch_market_info()
        
        print(f"{'='*75}")
        print(f"🚀 GRVT VOLUME GENERATOR - FULLY CONFIGURABLE")
        print(f"{'='*75}")
        print(f"Environment: {self.environment}")
        print(f"Market: {self.market}")
        print(f"Sub Account: {self.sub_account_id[:10]}...")
        print(f"Investment: ${self.investment:.2f} (Leverage: {self.leverage}x)")
        print(f"Effective Capital: ${self.investment * self.leverage:.2f}")
        print(f"\n🎯 TARGETS:")
        print(f"   Volume Goal: ${self.target_volume:,.0f} in {self.target_hours}h")
        print(f"   Hourly Goal: ${self.hourly_target:,.0f}")
        print(f"   Max Loss: ${self.max_loss:.2f}")
        print(f"\n⚙️  STRATEGY CONFIG:")
        print(f"   Spread: {self.spread_bps/100:.3f}% ({self.spread_bps} bps)")
        print(f"   Orders: {self.orders_per_side*2} total ({self.orders_per_side} each side)")
        print(f"   Order Size: {self.order_size_percent*100:.1f}% of capital")
        print(f"   Refresh: Every {self.refresh_interval}s")
        print(f"\n🛡️  RATE LIMIT PROTECTION:")
        print(f"   Delay Between Orders: {self.delay_between_orders}s")
        print(f"   Delay After Cancel: {self.delay_after_cancel}s")
        print(f"   Max Orders/Cycle: {self.max_orders_to_place} per side")
        print(f"   Status Updates: Every {self.status_interval}s")
        print(f"\n💡 PROJECTIONS:")
        print(f"   Est. Trades Needed: ~{self.trades_needed:,}")
        print(f"   Avg Trade Size: ${self.avg_trade_size:.2f}")
        print(f"   Trading Fee: {self.trading_fee_percent}% 🎉 ZERO GAS!")
        print(f"   Order Type: {'POST_ONLY' if self.use_post_only else 'LIMIT'}")
        print(f"{'='*75}\n")

    async def fetch_market_info(self):
        """Fetch market configuration"""
        try:
            print(f"📊 Fetching market info for {self.market}...")
            
            # Fetch all markets
            markets = await self.client.fetch_markets()
            
            for market in markets:
                if market['id'] == self.market:
                    self.market_info = market
                    
                    # Parse tick size and min size
                    self.tick_size = float(market.get('precision', {}).get('price', 0.01))
                    self.min_size = float(market.get('limits', {}).get('amount', {}).get('min', 0.001))
                    
                    print(f"✅ Market Info Loaded:")
                    print(f"   Symbol: {market['symbol']}")
                    print(f"   Tick Size: {self.tick_size}")
                    print(f"   Min Size: {self.min_size}")
                    print(f"   Status: {market.get('active', 'UNKNOWN')}")
                    return
                    
            print(f"⚠️  Market {self.market} not found")
            print(f"   Using defaults: tick_size=0.01, min_size=0.001")
            self.tick_size = 0.01
            self.min_size = 0.001
                    
        except Exception as e:
            print(f"⚠️  Error fetching market info: {e}")
            self.tick_size = 0.01
            self.min_size = 0.001

    async def get_orderbook(self):
        """Get current orderbook"""
        try:
            orderbook = await self.client.fetch_order_book(self.market)
            
            if orderbook and 'bids' in orderbook and 'asks' in orderbook:
                if orderbook['bids'] and orderbook['asks']:
                    best_bid = float(orderbook['bids'][0][0])
                    best_ask = float(orderbook['asks'][0][0])
                    mid_price = (best_bid + best_ask) / 2
                    spread_pct = ((best_ask - best_bid) / mid_price) * 100
                    
                    return {
                        'best_bid': best_bid,
                        'best_ask': best_ask,
                        'mid_price': mid_price,
                        'spread_pct': spread_pct
                    }
            return None
        except Exception as e:
            return None

    def round_price(self, price):
        """Round price to tick size"""
        if self.tick_size:
            import math
            if self.tick_size >= 1:
                decimals = 0
            else:
                decimals = abs(int(math.floor(math.log10(self.tick_size))))
            return round(price, decimals)
        return round(price, 2)

    def round_size(self, size):
        """Round size to min size"""
        if self.min_size:
            rounded = round(size / self.min_size) * self.min_size
            if rounded == 0 and size > 0:
                return self.min_size
            return rounded
        return round(size, 6)

    async def calculate_order_levels(self, orderbook):
        """Calculate order levels with configurable spread"""
        mid_price = orderbook['mid_price']
        best_bid = orderbook['best_bid']
        best_ask = orderbook['best_ask']
        
        spread = mid_price * (self.spread_bps / 10000)
        
        buy_levels = []
        sell_levels = []
        
        for i in range(self.orders_per_side):
            price = self.round_price(best_bid - (spread * i * 0.4))
            buy_levels.append(price)
        
        for i in range(self.orders_per_side):
            price = self.round_price(best_ask + (spread * i * 0.4))
            sell_levels.append(price)
        
        return buy_levels, sell_levels

    async def place_order(self, price, side, size):
        """Place single order"""
        try:
            self.client_order_id += 1
            
            # Place order using CCXT
            order = await self.client.create_order(
                symbol=self.market,
                type='limit',
                side='buy' if side == "BUY" else 'sell',
                amount=self.round_size(size),
                price=price,
                params={
                    'postOnly': self.use_post_only,
                    'clientOrderId': str(self.client_order_id)
                }
            )
            
            if order and 'id' in order:
                self.active_orders[order['id']] = {
                    'client_id': self.client_order_id,
                    'price': price,
                    'side': side,
                    'size': size,
                    'timestamp': time.time()
                }
                return True
            return False
                
        except Exception as e:
            if self.client_order_id <= 3:
                print(f"   ⚠️  Order error: {side} @ ${price:.2f} - {str(e)[:100]}")
            return False

    async def cancel_all_orders(self):
        """Cancel all active orders"""
        try:
            await self.client.cancel_all_orders(self.market)
            self.active_orders.clear()
        except Exception as e:
            pass

    async def refresh_orders(self):
        """Main order refresh loop"""
        print(f"🔄 Starting order refresh ({self.refresh_interval}s cycles)...\n")
        
        cycle = 0
        last_status_time = time.time()
        
        while self.running:
            try:
                cycle += 1
                cycle_start = time.time()
                
                # Get orderbook
                orderbook = await self.get_orderbook()
                if not orderbook:
                    if cycle <= 3:
                        print(f"   ⚠️  Cycle {cycle}: No orderbook data, retrying...")
                    await asyncio.sleep(self.refresh_interval)
                    continue
                
                # Print orderbook info for first few cycles
                if cycle <= 3:
                    print(f"\n📊 Cycle {cycle} - Orderbook:")
                    print(f"   Best Bid: ${orderbook['best_bid']:,.2f}")
                    print(f"   Best Ask: ${orderbook['best_ask']:,.2f}")
                    print(f"   Mid Price: ${orderbook['mid_price']:,.2f}")
                    print(f"   Spread: {orderbook['spread_pct']:.3f}%")
                
                # Cancel existing orders
                await self.cancel_all_orders()
                await asyncio.sleep(self.delay_after_cancel)
                
                # Calculate levels
                buy_levels, sell_levels = await self.calculate_order_levels(orderbook)
                
                # Calculate order size
                coin_size = (self.investment * self.leverage * self.order_size_percent) / orderbook['mid_price']
                
                if cycle <= 3:
                    print(f"   Order size: {coin_size:.6f} {self.market.split('_')[0]}")
                    print(f"   Placing {self.max_orders_to_place} buy + {self.max_orders_to_place} sell orders...")
                
                # Place buy orders
                placed_buy = 0
                for i, price in enumerate(buy_levels[:self.max_orders_to_place]):
                    if await self.place_order(price, "BUY", coin_size):
                        placed_buy += 1
                        if cycle <= 3 and i < 3:
                            print(f"   ✅ BUY @ ${price:,.2f}")
                    await asyncio.sleep(self.delay_between_orders)
                
                # Place sell orders
                placed_sell = 0
                for i, price in enumerate(sell_levels[:self.max_orders_to_place]):
                    if await self.place_order(price, "SELL", coin_size):
                        placed_sell += 1
                        if cycle <= 3 and i < 3:
                            print(f"   ✅ SELL @ ${price:,.2f}")
                    await asyncio.sleep(self.delay_between_orders)
                
                if cycle <= 3:
                    print(f"   Summary: {placed_buy} buy + {placed_sell} sell orders placed\n")
                
                # Print status
                if time.time() - last_status_time >= self.status_interval:
                    await self.print_status(orderbook, placed_buy, placed_sell)
                    last_status_time = time.time()
                
                # Hour rollover
                if (datetime.now() - self.hour_start).total_seconds() >= 3600:
                    self.hourly_stats.append({
                        'volume': self.current_hour_volume,
                        'trades': self.current_hour_trades
                    })
                    print(f"\n⏰ HOUR {len(self.hourly_stats)} COMPLETE:")
                    print(f"   Volume: ${self.current_hour_volume:,.0f}")
                    print(f"   Trades: {self.current_hour_trades:,}")
                    print(f"   Target: ${self.hourly_target:,.0f}\n")
                    
                    self.current_hour_volume = 0.0
                    self.current_hour_trades = 0
                    self.hour_start = datetime.now()
                
                # Safety check
                if self.trading_fee_percent > 0 and self.total_fees >= self.max_loss:
                    print(f"\n🛑 MAX LOSS REACHED: ${self.total_fees:.2f}")
                    self.running = False
                    break
                
                # Sleep
                cycle_time = time.time() - cycle_start
                sleep_time = max(0, self.refresh_interval - cycle_time)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                print(f"⚠️  Cycle error: {e}")
                await asyncio.sleep(self.refresh_interval)

    async def print_status(self, orderbook, placed_buy, placed_sell):
        """Print status update with real fills data"""
        runtime = datetime.now() - self.session_start
        hours_run = runtime.total_seconds() / 3600
        
        # Get real fills from API
        try:
            fills = await self.client.fetch_my_trades(self.market)
            if fills:
                # Count only fills from this session
                session_fills = [f for f in fills 
                               if f.get('timestamp', 0) >= int(self.session_start.timestamp() * 1000)]
                
                # Calculate real volume
                real_volume = sum(float(f.get('cost', 0)) for f in session_fills)
                real_trades = len(session_fills)
                
                self.total_volume = real_volume
                self.total_trades = real_trades
        except:
            pass
        
        volume_rate = self.total_volume / max(hours_run, 0.01)
        trade_rate = self.total_trades / max(hours_run, 0.01)
        projected = volume_rate * self.target_hours
        progress_pct = (self.total_volume / self.target_volume) * 100
        
        time_remaining = timedelta(hours=self.target_hours) - runtime
        hours_left = time_remaining.total_seconds() / 3600
        volume_left = self.target_volume - self.total_volume
        required_rate = volume_left / max(hours_left, 0.01) if hours_left > 0 else 0
        
        print(f"{'='*75}")
        print(f"⏱️  {str(runtime).split('.')[0]} elapsed | {max(0, hours_left):.1f}h left | Price: ${orderbook['mid_price']:,.2f}")
        print(f"📊 Orders: {placed_buy} BUY + {placed_sell} SELL | Spread: {orderbook['spread_pct']:.3f}%")
        print(f"\n💰 VOLUME (REAL from API):")
        print(f"   Current: ${self.total_volume:,.0f} / ${self.target_volume:,.0f} ({progress_pct:.1f}%)")
        print(f"   Trades: {self.total_trades:,} ({trade_rate:.0f}/hour)")
        print(f"\n📈 PERFORMANCE:")
        print(f"   Current Rate: ${volume_rate:,.0f}/hour")
        print(f"   {self.target_hours}h Projection: ${projected:,.0f}")
        print(f"   Required Rate: ${required_rate:,.0f}/hour")
        print(f"   Status: {'✅ ON TRACK' if volume_rate >= required_rate * 0.9 else '⚠️  SPEED UP'}")
        print(f"\n💸 COSTS:")
        print(f"   🎉 ZERO GAS FEES - ZKSync powered!")
        print(f"   Loss (spread): ${self.total_fees:.2f}")
        print(f"{'='*75}\n")

    def stop_bot(self, signum=None, frame=None):
        """Stop bot gracefully"""
        print("\nSTOPPING BOT...")
        self.running = False

    async def run(self):
        """Main execution"""
        signal.signal(signal.SIGINT, self.stop_bot)
        
        try:
            await self.init()
            await self.refresh_orders()
            
        except KeyboardInterrupt:
            self.stop_bot()
        except Exception as e:
            print(f"❌ Fatal Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("\n🧹 Cleaning up...")
            
            if self.client:
                await self.cancel_all_orders()
            
            if self.session_start:
                runtime = datetime.now() - self.session_start
                hours_run = runtime.total_seconds() / 3600
                
                print(f"\n{'='*75}")
                print(f"📊 FINAL REPORT - GRVT")
                print(f"{'='*75}")
                print(f"Runtime: {str(runtime).split('.')[0]} ({hours_run:.2f} hours)")
                print(f"\n💰 VOLUME:")
                print(f"   Total: ${self.total_volume:,.2f}")
                print(f"   Target: ${self.target_volume:,.0f}")
                print(f"   Achievement: {(self.total_volume/self.target_volume)*100:.1f}%")
                print(f"\n📈 TRADES:")
                print(f"   Total: {self.total_trades:,}")
                print(f"   Avg/Hour: {self.total_trades/max(hours_run,0.01):.0f}")
                print(f"\n💸 COSTS:")
                print(f"   🎉 ZERO GAS FEES!")
                print(f"   Loss: ${self.total_fees:.2f} (spread only)")
                print(f"{'='*75}\n")
            
            if self.client:
                await self.client.close()
            
            print("👋 Bot stopped\n")

if __name__ == "__main__":
    bot = GRVTVolumeBot()
    asyncio.run(bot.run())

import os
import time
import asyncio
from datetime import datetime, timedelta

# Load .env BEFORE everything
from dotenv import load_dotenv
load_dotenv()

# Get values from .env immediately
api_key = os.getenv('GRVT_API_KEY')
private_key = os.getenv('GRVT_PRIVATE_KEY')
trading_account_id = os.getenv('GRVT_SUB_ACCOUNT_ID') or os.getenv('GRVT_TRADING_ACCOUNT_ID')
environment = os.getenv('ENVIRONMENT', 'testnet')

# Validate
if not api_key:
    print("❌ ERROR: GRVT_API_KEY not found in .env!")
    exit(1)
if not private_key:
    print("❌ ERROR: GRVT_PRIVATE_KEY not found in .env!")
    print(f"   Current value: {private_key if private_key else 'None/Empty'}")
    exit(1)
if not trading_account_id:
    print("❌ ERROR: GRVT_SUB_ACCOUNT_ID not found in .env!")
    exit(1)

# Set environment variables BEFORE any SDK imports
os.environ['GRVT_API_KEY'] = api_key
os.environ['GRVT_PRIVATE_KEY'] = private_key
os.environ['GRVT_TRADING_ACCOUNT_ID'] = str(trading_account_id)
os.environ['GRVT_ENV'] = environment
os.environ['GRVT_END_POINT_VERSION'] = 'v1'
os.environ['GRVT_WS_STREAM_VERSION'] = 'v1'

# Verify environment variables are set
print(f"🔑 Verifying environment variables BEFORE SDK import:")
print(f"  os.environ['GRVT_API_KEY']: {os.environ.get('GRVT_API_KEY', 'NOT SET')[:10]}...")
print(f"  os.environ['GRVT_PRIVATE_KEY']: {os.environ.get('GRVT_PRIVATE_KEY', 'NOT SET')[:10]}... (len={len(os.environ.get('GRVT_PRIVATE_KEY', ''))})")
print(f"  os.environ['GRVT_TRADING_ACCOUNT_ID']: {os.environ.get('GRVT_TRADING_ACCOUNT_ID', 'NOT SET')}")
print(f"  os.environ['GRVT_ENV']: {os.environ.get('GRVT_ENV', 'NOT SET')}")
print()

# NOW import SDK - it should read the env vars we just set
from pysdk.grvt_ccxt_pro import GrvtCcxtPro
from pysdk.grvt_ccxt_env import GrvtEnv

class GRVTVolumeBot:
    def __init__(self):
        # Market & Trading Settings
        self.market = os.getenv('MARKET', 'BTC_USDT_Perp')
        self.leverage = int(os.getenv('LEVERAGE', '10'))
        self.investment_usdc = float(os.getenv('INVESTMENT_USDC', '10'))
        
        # Volume Target Settings
        self.target_volume = float(os.getenv('TARGET_VOLUME', '100000'))
        self.max_loss = float(os.getenv('MAX_LOSS', '10'))
        self.target_hours = float(os.getenv('TARGET_HOURS', '24'))
        
        # Strategy Parameters
        self.spread_bps = float(os.getenv('SPREAD_BPS', '2'))
        self.orders_per_side = int(os.getenv('ORDERS_PER_SIDE', '10'))
        self.order_size_percent = float(os.getenv('ORDER_SIZE_PERCENT', '0.1'))
        self.refresh_interval = float(os.getenv('REFRESH_INTERVAL', '2.0'))
        
        # Rate Limit Protection
        self.delay_between_orders = float(os.getenv('DELAY_BETWEEN_ORDERS', '0.05'))
        self.delay_after_cancel = float(os.getenv('DELAY_AFTER_CANCEL', '0.3'))
        self.status_interval = int(os.getenv('STATUS_INTERVAL', '30'))
        self.max_orders_to_place = int(os.getenv('MAX_ORDERS_TO_PLACE', '10'))
        
        # Advanced Settings
        self.use_post_only = os.getenv('USE_POST_ONLY', 'true').lower() == 'true'
        
        # Initialize client
        self.client = None
        self.start_time = None
        self.total_volume = 0
        self.total_trades = 0
        self.total_loss = 0
        self.cycle_count = 0
        
    async def initialize(self):
        """Initialize GRVT client"""
        # Map environment string to GrvtEnv enum
        env_string = os.getenv('ENVIRONMENT', 'testnet').lower()
        env_map = {
            'testnet': GrvtEnv.TESTNET,
            'prod': GrvtEnv.PROD,
            'production': GrvtEnv.PROD,
            'dev': GrvtEnv.DEV,
            'staging': GrvtEnv.STAGING
        }
        
        env = env_map.get(env_string, GrvtEnv.TESTNET)
        
        # Get trading account ID
        trading_account_id = os.getenv('GRVT_SUB_ACCOUNT_ID') or os.getenv('GRVT_TRADING_ACCOUNT_ID')
        
        if not trading_account_id:
            print("❌ ERROR: GRVT_SUB_ACCOUNT_ID is not set in .env file!")
            print("Please add: GRVT_SUB_ACCOUNT_ID=your_trading_account_id")
            raise ValueError("Missing GRVT_SUB_ACCOUNT_ID")
        
        # Initialize GRVT CCXT Pro client
        self.client = GrvtCcxtPro(env=env)
        
        # CRITICAL: SDK does NOT read from environment variables!
        # Must set all these attributes manually:
        self.client._api_key = os.getenv('GRVT_API_KEY')
        self.client._private_key = os.getenv('GRVT_PRIVATE_KEY')
        self.client._trading_account_id = trading_account_id
        
        print(f"✅ Set client attributes:")
        print(f"  _api_key: {self.client._api_key[:10] if self.client._api_key else 'NOT SET'}...")
        print(f"  _private_key: {self.client._private_key[:10] if self.client._private_key else 'NOT SET'}... (len={len(self.client._private_key) if self.client._private_key else 0})")
        print(f"  _trading_account_id: {self.client._trading_account_id}")
        
        # Verify all are set
        if not self.client._api_key:
            raise ValueError("Failed to set _api_key")
        if not self.client._private_key:
            raise ValueError("Failed to set _private_key")
        if not self.client._trading_account_id:
            raise ValueError("Failed to set _trading_account_id")
        
        # Load markets
        print("📡 Loading markets...")
        try:
            await self.client.load_markets()
            print(f"✅ Loaded {len(self.client.markets)} markets")
            
            # Check if our market exists
            if self.market in self.client.markets:
                print(f"✅ Market {self.market} found")
            else:
                print(f"❌ Market {self.market} not found!")
                print(f"Available markets: {list(self.client.markets.keys())[:10]}...")
                raise ValueError(f"Market {self.market} not available")
        except Exception as e:
            print(f"❌ Error loading markets: {e}")
            raise
        
        print("🚀 GRVT VOLUME GENERATOR - FULLY CONFIGURABLE")
        print("=" * 75)
        print(f"Environment: {os.getenv('ENVIRONMENT', 'testnet').upper()}")
        print(f"Market: {self.market}")
        print(f"Sub Account: {os.getenv('GRVT_SUB_ACCOUNT_ID', '')[:10]}...")
        print(f"Investment: ${self.investment_usdc:.2f} (Leverage: {self.leverage}x)")
        print(f"Effective Capital: ${self.investment_usdc * self.leverage:.2f}")
        print()
        print("🎯 TARGETS:")
        print(f"  Volume Goal: ${self.target_volume:,.0f} in {self.target_hours}h")
        print(f"  Hourly Goal: ${self.target_volume/self.target_hours:,.0f}")
        print(f"  Max Loss: ${self.max_loss:.2f}")
        print()
        print("⚙️ STRATEGY CONFIG:")
        print(f"  Spread: {self.spread_bps/100:.3f}% ({self.spread_bps:.0f} bps)")
        print(f"  Orders: {self.orders_per_side * 2} total ({self.orders_per_side} each side)")
        print(f"  Order Size: {self.order_size_percent * 100:.1f}% of capital")
        print(f"  Refresh: Every {self.refresh_interval:.1f}s")
        print()
        
        self.start_time = datetime.now()
        
    async def get_orderbook(self):
        """Get current orderbook"""
        try:
            orderbook = await self.client.fetch_order_book(self.market)
            
            # Debug output on first cycle
            if self.cycle_count == 1:
                print(f"DEBUG - Orderbook type: {type(orderbook)}")
                print(f"DEBUG - Orderbook keys: {orderbook.keys() if isinstance(orderbook, dict) else 'Not a dict'}")
                if 'bids' in orderbook:
                    print(f"DEBUG - Bids type: {type(orderbook['bids'])}")
                    if orderbook['bids']:
                        print(f"DEBUG - First bid: {orderbook['bids'][0]}")
            
            if not orderbook or not isinstance(orderbook, dict):
                return None
                
            if 'bids' not in orderbook or 'asks' not in orderbook:
                return None
            
            bids = orderbook['bids']
            asks = orderbook['asks']
            
            if not bids or not asks:
                return None
            
            # GRVT format: list of dicts with 'price' and 'size' keys
            # [{'price': '121250.0', 'size': '0.013', 'num_orders': 3}, ...]
            if isinstance(bids[0], dict):
                best_bid_price = float(bids[0]['price'])
                best_ask_price = float(asks[0]['price'])
            # Standard CCXT format: [[price, size], ...]
            elif isinstance(bids[0], (list, tuple)):
                best_bid_price = float(bids[0][0])
                best_ask_price = float(asks[0][0])
            else:
                print(f"DEBUG - Unknown bid format: {type(bids[0])}")
                return None
            
            if best_bid_price == 0 or best_ask_price == 0:
                return None
                
            mid_price = (best_bid_price + best_ask_price) / 2
            spread = ((best_ask_price - best_bid_price) / mid_price) * 100
            
            return {
                'best_bid': best_bid_price,
                'best_ask': best_ask_price,
                'mid_price': mid_price,
                'spread': spread
            }
        except Exception as e:
            print(f"❌ Error getting orderbook: {e}")
            import traceback
            if self.cycle_count <= 2:
                print(f"DEBUG - Traceback: {traceback.format_exc()}")
            return None
            
    async def get_account_volume(self):
        """Get actual volume from trades"""
        try:
            # fetch_my_trades(symbol) - trading_account_id should be set on client
            trades = await self.client.fetch_my_trades(self.market)

            # Debug on first cycle
            if self.cycle_count == 1:
                print(f"DEBUG - trades type: {type(trades)}")
                print(f"DEBUG - trades value: {trades}")

            # Handle if trades is not a list
            if not isinstance(trades, list):
                if self.cycle_count <= 2:
                    print(f"⚠️ trades is not a list: {type(trades)}")
                return self.total_volume, self.total_trades

            volume = 0
            trade_count = 0

            for trade in trades:
                # Handle different trade formats
                if not isinstance(trade, dict):
                    continue

                # Try to get timestamp
                timestamp = trade.get('timestamp') or trade.get('time') or 0
                if timestamp == 0:
                    continue

                trade_time = datetime.fromtimestamp(timestamp / 1000)
                if trade_time >= self.start_time:
                    # Try different cost fields
                    cost = trade.get('cost') or trade.get('amount') or 0
                    volume += float(cost)
                    trade_count += 1

            return volume, trade_count
        except Exception as e:
            if "trading_account_id" not in str(e) or self.cycle_count > 3:
                print(f"⚠️ Error getting trades: {e}")
                if self.cycle_count <= 2:
                    import traceback
                    print(f"DEBUG - Traceback:\n{traceback.format_exc()}")
            return self.total_volume, self.total_trades
            
    async def cancel_all_orders(self):
        """Cancel all open orders"""
        try:
            # cancel_all_orders(symbol) - no params parameter
            await self.client.cancel_all_orders(self.market)
            await asyncio.sleep(self.delay_after_cancel)
        except Exception as e:
            # Suppress trading_account_id error on first few attempts
            if "trading_account_id" not in str(e) or self.cycle_count > 3:
                print(f"⚠️ Error canceling orders: {e}")
            
    def round_price(self, price):
        """Round price to valid tick size (0.1 for BTC_USDT_Perp)"""
        tick_size = 0.1
        return round(price / tick_size) * tick_size

    def round_size(self, size):
        """Round order size to valid step size (0.001 for BTC - larger step)"""
        step_size = 0.001
        return round(size / step_size) * step_size

    async def place_orders(self, orderbook):
        """Place buy and sell orders"""
        mid_price = orderbook['mid_price']
        spread_amount = mid_price * (self.spread_bps / 10000)

        # Calculate order size
        capital = self.investment_usdc * self.leverage
        order_value = capital * self.order_size_percent
        order_size = order_value / mid_price
        order_size = self.round_size(order_size)  # Round to step size

        # Get trading account ID
        trading_account_id = os.getenv('GRVT_SUB_ACCOUNT_ID') or os.getenv('GRVT_TRADING_ACCOUNT_ID')

        buy_orders = 0
        sell_orders = 0

        print(f"\n📊 Cycle {self.cycle_count} - Orderbook:")
        print(f"  Best Bid: ${orderbook['best_bid']:,.2f}")
        print(f"  Best Ask: ${orderbook['best_ask']:,.2f}")
        print(f"  Mid Price: ${mid_price:,.2f}")
        print(f"  Spread: {orderbook['spread']:.3f}%")
        print(f"  Order size: {order_size:.6f} {self.market.split('_')[0]}")
        print(f"\nPlacing {self.orders_per_side} buy + {self.orders_per_side} sell orders...")

        # Place buy orders
        for i in range(min(self.orders_per_side, self.max_orders_to_place)):
            try:
                price = mid_price - spread_amount - (i * 0.01 * mid_price)
                price = self.round_price(price)  # Round to tick size
                
                # GRVT requires sub_account_id in the order params
                params = {
                    'sub_account_id': trading_account_id
                }
                if self.use_post_only:
                    params['post_only'] = True  # Try snake_case
                
                # Debug on first order
                if i == 0 and self.cycle_count == 1:
                    print(f"DEBUG - Calling create_order with:")
                    print(f"  symbol: {self.market}")
                    print(f"  side: buy")
                    print(f"  amount: {order_size}")
                    print(f"  price: {price}")
                    print(f"  params: {params}")
                
                # CCXT Pro create_order requires order_type as second parameter
                # Must be 'limit' or 'market', not 'buy'/'sell'
                await self.client.create_order(
                    self.market,
                    'limit',  # order_type: 'limit' or 'market'
                    'buy',    # side: 'buy' or 'sell'
                    order_size,
                    price,
                    params
                )
                
                buy_orders += 1
                if i == 0:
                    print(f"✅ BUY @ ${price:,.2f}")
                    
                await asyncio.sleep(self.delay_between_orders)
            except Exception as e:
                if "post" not in str(e).lower() or i == 0:
                    print(f"⚠️ Buy order {i+1} failed: {e}")
                    if i == 0 and self.cycle_count == 1:
                        import traceback
                        print(f"DEBUG - Full traceback:\n{traceback.format_exc()}")
                if i == 0:
                    break  # Stop if first order fails
                
        # Place sell orders
        for i in range(min(self.orders_per_side, self.max_orders_to_place)):
            try:
                price = mid_price + spread_amount + (i * 0.01 * mid_price)
                price = self.round_price(price)  # Round to tick size

                params = {
                    'sub_account_id': trading_account_id
                }
                if self.use_post_only:
                    params['post_only'] = True
                
                await self.client.create_order(
                    self.market,
                    'limit',  # order_type: 'limit' or 'market'
                    'sell',   # side: 'buy' or 'sell'
                    order_size,
                    price,
                    params
                )
                
                sell_orders += 1
                if i == 0:
                    print(f"✅ SELL @ ${price:,.2f}")
                    
                await asyncio.sleep(self.delay_between_orders)
            except Exception as e:
                if "post" not in str(e).lower() or i == 0:
                    print(f"⚠️ Sell order {i+1} failed: {e}")
                if i == 0:
                    break
                
        print(f"\nSummary: {buy_orders} buy + {sell_orders} sell orders placed")
        
    def print_status(self, orderbook):
        """Print status update"""
        elapsed = datetime.now() - self.start_time
        remaining = timedelta(hours=self.target_hours) - elapsed
        
        # Format time
        elapsed_str = str(elapsed).split('.')[0]
        remaining_str = f"{remaining.total_seconds()/3600:.1f}h"
        
        # Calculate metrics
        volume_pct = (self.total_volume / self.target_volume) * 100
        current_rate = (self.total_volume / elapsed.total_seconds()) * 3600 if elapsed.total_seconds() > 0 else 0
        projected_24h = current_rate * 24
        required_rate = self.target_volume / self.target_hours
        
        print("\n" + "=" * 75)
        print(f"⏱️ {elapsed_str} elapsed | {remaining_str} left | Price: ${orderbook['mid_price']:,.2f}")
        print(f"📊 Orders: {self.orders_per_side} BUY + {self.orders_per_side} SELL | Spread: {orderbook['spread']:.3f}%")
        print(f"\n💰 VOLUME (from trades):")
        print(f"  Current: ${self.total_volume:,.0f} / ${self.target_volume:,.0f} ({volume_pct:.1f}%)")
        print(f"  Trades: {self.total_trades}")
        print(f"\n📈 PERFORMANCE:")
        print(f"  Current Rate: ${current_rate:,.0f}/hour")
        print(f"  24h Projection: ${projected_24h:,.0f}")
        print(f"  Required Rate: ${required_rate:,.0f}/hour")
        print(f"\n💸 COSTS:")
        print(f"  🎉 ZERO GAS FEES - ZKSync powered!")
        print(f"  Loss (spread): ${self.total_loss:.2f}")
        print("=" * 75)
        
    async def run(self):
        """Main bot loop"""
        await self.initialize()
        
        print("🔄 Starting order refresh ({:.1f}s cycles)...\n".format(self.refresh_interval))
        
        last_status = time.time()
        
        try:
            while True:
                self.cycle_count += 1
                
                # Get orderbook
                orderbook = await self.get_orderbook()
                if not orderbook:
                    print("⚠️ Failed to get orderbook, retrying...")
                    await asyncio.sleep(5)
                    continue
                    
                # Cancel existing orders
                await self.cancel_all_orders()
                
                # Place new orders
                await self.place_orders(orderbook)
                
                # Update volume from trades
                self.total_volume, self.total_trades = await self.get_account_volume()
                
                # Estimate loss
                self.total_loss = self.total_volume * (self.spread_bps / 10000)
                
                # Print status
                if time.time() - last_status >= self.status_interval:
                    self.print_status(orderbook)
                    last_status = time.time()
                    
                # Check stop conditions
                if self.total_loss >= self.max_loss:
                    print(f"\n🛑 Max loss reached: ${self.total_loss:.2f}")
                    break
                    
                if self.total_volume >= self.target_volume:
                    print(f"\n🎉 Target volume reached: ${self.total_volume:,.0f}")
                    break
                    
                elapsed = datetime.now() - self.start_time
                if elapsed >= timedelta(hours=self.target_hours):
                    print(f"\n⏰ Time limit reached: {self.target_hours}h")
                    break
                    
                # Wait for next cycle
                await asyncio.sleep(self.refresh_interval)
                
        except KeyboardInterrupt:
            print("\n\n⚠️ Stopping gracefully...")
            await self.cancel_all_orders()
            if orderbook:
                self.print_status(orderbook)
            print("\n✅ Bot stopped.")
        finally:
            await self.client.close()
            
if __name__ == "__main__":
    bot = GRVTVolumeBot()
    asyncio.run(bot.run())

# GRVT Volume Bot

Automated volume generation bot for GRVT - a ZKSync-powered decentralized perpetual exchange with zero gas fees.

## Features

- Zero gas fees (ZKSync Hyperchain)
- Fully configurable via `.env` file
- Ultra-tight spread market making strategy
- Real-time volume tracking from API
- Support for perpetual contracts
- Auto order refresh and placement
- Python SDK integration (CCXT-compatible)
- Testnet and production support

## Requirements

- Python 3.10 or higher
- pip package manager
- GRVT account (testnet or mainnet)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/grvt-volume-bot.git
cd grvt-volume-bot
```

### 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Configuration

### Step 1: Create GRVT Account

1. Visit [GRVT Testnet](https://testnet.grvt.io/exchange/sign-up) or [GRVT Prod](https://grvt.io)
2. Create account (Personal or Business)
3. Link your wallet (existing or create web wallet)
4. Complete two-tier account setup:
   - **Funding Account**: For deposits/withdrawals
   - **Trading Account**: For derivative trading
5. For testnet: Mint tokens at https://testnet.grvt.io/exchange/deposit

### Step 2: Create API Key

1. Go to [API Keys](https://testnet.grvt.io/exchange/account/api-keys)
2. Click **Create API Key**
3. Select permissions:
   - ✅ **Trade** (required for trading)
   - ✅ **View** (required for reading data)
4. **Copy and save** your API Key (shown only once!)
5. Note your **Sub Account ID** (Trading Account ID)

### Step 3: Configure Environment

```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

Edit the `.env` file:

```bash
# ========================================
# GRVT API Configuration
# ========================================
GRVT_API_KEY=your_api_key_here          # API Key from GRVT
GRVT_SUB_ACCOUNT_ID=your_sub_account_id # Trading Account ID
ENVIRONMENT=TESTNET                      # TESTNET, DEV, or PROD

# ========================================
# Market & Trading Settings
# ========================================
MARKET=BTC_USDT_Perp                    # Market to trade
LEVERAGE=10                              # Leverage multiplier (1-20x)
INVESTMENT_USDC=10                       # Investment amount in USDC

# ========================================
# Volume Target Settings
# ========================================
TARGET_VOLUME=100000                     # Target volume in USD
MAX_LOSS=10                              # Maximum loss in USD
TARGET_HOURS=24                          # Timeframe in hours

# ========================================
# Strategy Parameters
# ========================================
SPREAD_BPS=2                             # Spread in basis points (0.02%)
ORDERS_PER_SIDE=10                       # Orders per side (10+10=20)
ORDER_SIZE_PERCENT=0.1                   # Order size % of capital
REFRESH_INTERVAL=2.0                     # Refresh interval (seconds)

# ========================================
# Rate Limit Protection
# ========================================
DELAY_BETWEEN_ORDERS=0.05
DELAY_AFTER_CANCEL=0.3
STATUS_INTERVAL=30
MAX_ORDERS_TO_PLACE=10

# ========================================
# Advanced Settings
# ========================================
USE_POST_ONLY=true
TRADING_FEE_PERCENT=0.0                  # 0% - Zero gas!
```

## Supported Markets

GRVT supports perpetual contracts:

- `BTC_USDT_Perp` - Bitcoin/USDT Perpetual
- `ETH_USDT_Perp` - Ethereum/USDT Perpetual
- `SOL_USDT_Perp` - Solana/USDT Perpetual
- And many more...

Check available markets at [GRVT Market Data](https://api-docs.grvt.io/market_data_api/)

## Usage

### Run the bot

```bash
python3 bot.py
```

### Expected Output

```
🚀 GRVT VOLUME GENERATOR - FULLY CONFIGURABLE
===========================================================================
Environment: TESTNET
Market: BTC_USDT_Perp
Sub Account: 0x1234567...
Investment: $10.00 (Leverage: 10x)
Effective Capital: $100.00

🎯 TARGETS:
   Volume Goal: $100,000 in 24h
   Hourly Goal: $4,166
   Max Loss: $10.00

⚙️  STRATEGY CONFIG:
   Spread: 0.020% (2 bps)
   Orders: 20 total (10 each side)
   Order Size: 10.0% of capital
   Refresh: Every 2.0s

🔄 Starting order refresh (2.0s cycles)...

📊 Cycle 1 - Orderbook:
   Best Bid: $95,432.10
   Best Ask: $95,432.90
   Mid Price: $95,432.50
   Spread: 0.008%
   Order size: 0.000105 BTC
   Placing 10 buy + 10 sell orders...
   ✅ BUY @ $95,432.00
   ✅ SELL @ $95,433.00
   Summary: 10 buy + 10 sell orders placed

===========================================================================
⏱️  0:00:31 elapsed | 23.9h left | Price: $95,432.50
📊 Orders: 10 BUY + 10 SELL | Spread: 0.008%

💰 VOLUME (REAL from API):
   Current: $250 / $100,000 (0.3%)
   Trades: 8

📈 PERFORMANCE:
   Current Rate: $480/hour
   24h Projection: $11,520
   Required Rate: $4,166/hour

💸 COSTS:
   🎉 ZERO GAS FEES - ZKSync powered!
   Loss (spread): $0.12
===========================================================================
```

### Stop the bot

Press `Ctrl+C` to stop gracefully.

## Strategy Presets

### Conservative (Safe)

```bash
SPREAD_BPS=5
ORDERS_PER_SIDE=8
ORDER_SIZE_PERCENT=0.15
REFRESH_INTERVAL=3.0
```

### Balanced (Recommended)

```bash
SPREAD_BPS=2
ORDERS_PER_SIDE=10
ORDER_SIZE_PERCENT=0.1
REFRESH_INTERVAL=2.0
```

### Aggressive (High volume)

```bash
SPREAD_BPS=1
ORDERS_PER_SIDE=15
ORDER_SIZE_PERCENT=0.05
REFRESH_INTERVAL=1.0
```

## Tips for Success

### Maximize Volume

1. Use tight spreads (`SPREAD_BPS=1`)
2. More orders (`ORDERS_PER_SIDE=15`)
3. Fast refresh (`REFRESH_INTERVAL=1.0`)
4. Smaller orders (`ORDER_SIZE_PERCENT=0.05`)

### Minimize Loss

1. Wider spreads (`SPREAD_BPS=5`)
2. Larger orders (`ORDER_SIZE_PERCENT=0.2`)
3. POST_ONLY mode (`USE_POST_ONLY=true`)

## Troubleshooting

### Authentication Error

**Cause**: Invalid API key or Sub Account ID

**Solution**:
- Verify `GRVT_API_KEY` in `.env`
- Verify `GRVT_SUB_ACCOUNT_ID` matches your Trading Account
- Check API key permissions (Trade + View required)

### Orders not filling

**Causes**:
- Spread too tight
- POST_ONLY mode
- Low market liquidity

**Solutions**:
- Increase `SPREAD_BPS` to 3-5
- Set `USE_POST_ONLY=false`
- Try a more liquid market (BTC, ETH)

### "Size below minimum" error

**Cause**: Order size too small for market

**Solutions**:
- Increase `INVESTMENT_USDC`
- Increase `ORDER_SIZE_PERCENT`
- Check market's minimum size requirement

### Connection timeout

**Cause**: Network or GRVT API issues

**Solutions**:
- Check internet connection
- Verify GRVT API status
- Try different environment (TESTNET vs PROD)

### No orderbook data

**Cause**: Market not active or incorrect symbol

**Solutions**:
- Verify market symbol format (e.g., `BTC_USDT_Perp`)
- Check market is active on GRVT
- Try different market

## Safety & Risk Management

### Important Warnings

⚠️ **You can lose your entire investment**
⚠️ **This bot is for volume generation, not profit**
⚠️ **Test on testnet first before using real funds**
⚠️ **Never share your API keys**
⚠️ **Monitor the bot closely**

### Risk Mitigation

1. **Start small** - Test with $10-20 first
2. **Use testnet** - Practice on testnet.grvt.io
3. **Monitor closely** - Watch first hour carefully
4. **Set stop-loss** - Use `MAX_LOSS` parameter
5. **Limited permissions** - Use API keys with Trade-only permissions

## GRVT Architecture

GRVT is a hybrid exchange:
- **Off-chain matching** - High throughput, low latency
- **On-chain settlement** - ZK proofs on Ethereum
- **Zero gas fees** - No gas costs for trading
- **Self-custodial** - Funds secured by smart contracts

## Rate Limits

GRVT rate limits are generous:
- Trade endpoints: High limits per account
- Market data: Public, high rate limits
- WebSocket: Real-time updates

Bot stays well within limits with default settings.

## Advanced Features

### Multi-market Trading

Run multiple bots on different markets:

```bash
# Terminal 1 - BTC
MARKET=BTC_USDT_Perp python3 bot.py

# Terminal 2 - ETH
MARKET=ETH_USDT_Perp python3 bot.py

# Terminal 3 - SOL
MARKET=SOL_USDT_Perp python3 bot.py
```

### Background Execution

Run bot in background:

```bash
nohup python3 bot.py > bot.log 2>&1 &
tail -f bot.log
```

### Custom Logging

```bash
python3 bot.py 2>&1 | tee -a logs/bot_$(date +%Y%m%d_%H%M%S).log
```

## API Documentation

- **GRVT Docs**: [api-docs.grvt.io](https://api-docs.grvt.io/)
- **Python SDK**: [github.com/gravity-technologies/grvt-pysdk](https://github.com/gravity-technologies/grvt-pysdk)
- **API Setup Guide**: [api-docs.grvt.io/api_setup](https://api-docs.grvt.io/api_setup/)

## Environment URLs

### Testnet
- **Web**: https://testnet.grvt.io
- **API**: https://edge.testnet.grvt.io
- **Trades**: https://trades.testnet.grvt.io

### Production
- **Web**: https://grvt.io
- **API**: https://edge.grvt.io
- **Trades**: https://trades.grvt.io

## Performance Metrics

Typical performance with default settings:

- **Volume per hour**: $500 - $2,000
- **Fill rate**: 20-80 fills/hour
- **Loss rate**: 0.05-0.15% of volume (spread only)
- **Uptime**: 23.5+ hours per day

## Comparison with Other DEXs

| Feature | GRVT | Paradex | Lighter |
|---------|------|---------|---------|
| **Gas Fees** | Zero | Zero | Zero |
| **Technology** | ZKSync | Starknet | Custom |
| **Liquidity** | High | Very High | Medium |
| **Markets** | 50+ | 250+ | 10 |
| **SDK** | Python (CCXT) | Python | Python |
| **Settlement** | On-chain ZK | On-chain | Hybrid |

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/grvt-volume-bot/issues)
- **GRVT Docs**: [api-docs.grvt.io](https://api-docs.grvt.io)
- **GRVT Help**: [help.grvt.io](https://help.grvt.io)
- **Email**: [email protected]

## License

MIT License - see LICENSE file for details

## Disclaimer

This software is provided "as is" without warranty of any kind. Trading cryptocurrencies involves substantial risk of loss. Use at your own risk. The authors are not responsible for any financial losses incurred through the use of this bot.

**This bot is designed for volume generation and market making, not profit generation. You will likely lose money using this bot. Only use funds you can afford to lose.**

---

**Built for GRVT - Zero gas perpetual trading powered by ZKSync**

# Binance Futures Testnet — Trading Bot

A Python CLI bot that places **MARKET** and **LIMIT** orders on the [Binance Futures Testnet (USDT-M)](https://testnet.binancefuture.com).

---

## Project Structure

```
basic-trading-cli/
├── trading_bot/
│   ├── __init__.py
│   ├── client.py           # REST client (signing, HTTP, error mapping)
│   ├── orders.py           # Order orchestration + result objects
│   ├── validators.py       # Input validation (independent of I/O layer)
│   └── logging_config.py   # Structured logging → file + console
├── logs/
│   └── sample_order.log
├── cli.py                  # CLI entry point (argparse + interactive menu)
├── .env                    # Your API credentials (never commit this)
├── .gitignore
├── README.md
└── requirements.txt
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/sleepyUjjal/basic-trading-cli.git
cd basic-trading-cli
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get Binance Futures Testnet credentials

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with GitHub or create an account
3. Navigate to **API Management** → click **Generate Key**
4. Copy your **API Key** and **Secret Key**
5. On the dashboard, click **Get** next to USDT to fund your testnet wallet

### 5. Create a `.env` file in the project root

```bash
touch .env
```

Add your credentials:

```
BINANCE_TESTNET_API_KEY=your_api_key_here
BINANCE_TESTNET_API_SECRET=your_api_secret_here
```

> ⚠️ Never commit `.env` to Git. It is already listed in `.gitignore`.

---

## Running the Bot

There are two ways to use the bot: **interactive menu** or **direct commands**.

---

### Option A — Interactive Menu (recommended for first use)

```bash
python cli.py interactive
```

You will see:

```
╔══════════════════════════════════════════════╗
║    Binance Futures Testnet — Trading Bot     ║
╚══════════════════════════════════════════════╝

✔ Connected to Binance Futures Testnet

Main Menu:
  [1] Place Order
  [2] Check Balance
  [3] Ping / Server Time
  [q] Quit

  Enter choice:
```

Follow the prompts to place an order:

```
── Place New Order ──────────────────────────────
  Symbol (e.g. BTCUSDT) [BTCUSDT]: BTCUSDT
  Side   [BUY / SELL] [BUY]: BUY
  Type   [MARKET / LIMIT] [MARKET]: MARKET
  Quantity: 0.002

Summary:
  BUY MARKET 0.002 BTCUSDT

Confirm? [y/N]: y
```

---

### Option B — Direct Commands

#### Test connectivity

```bash
python cli.py ping
```

#### Check account balance

```bash
python cli.py balance
```

#### Place a MARKET order

```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.002
```

#### Place a LIMIT order

```bash
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.002 --price 100000
```

#### Enable debug logging

```bash
python cli.py --log-level DEBUG place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.002
```

---

## Example Output

```
Order Request:
  Symbol    : BTCUSDT
  Side      : BUY
  Type      : MARKET
  Quantity  : 0.002

╔══════════════════════════════════════╗
║         ORDER PLACED SUCCESSFULLY     ║
╚══════════════════════════════════════╝
  Order ID     : 3865920
  Symbol       : BTCUSDT
  Side         : BUY
  Type         : MARKET
  Status       : FILLED
  Orig Qty     : 0.002
  Executed Qty : 0.002
  Avg Price    : 97854.30
```

---

## Logging

Logs are written to `logs/trading_bot_YYYYMMDD.log` and also printed to the console.

| Level | What gets logged                                    |
|-------|-----------------------------------------------------|
| INFO  | Order requests, responses, success/failure events   |
| DEBUG | Raw HTTP params, API response bodies, all internals |
| ERROR | API errors, network failures, validation failures   |

Sample log files from real testnet orders are included in `logs/`.

---

## Valid Symbols

The bot trades futures pairs, not individual assets. Use pairs like:

| Pair    | Description      |
|---------|------------------|
| BTCUSDT | Bitcoin / USDT   |
| ETHUSDT | Ethereum / USDT  |
| BNBUSDT | BNB / USDT       |

> ✖ `USDC`, `BTC`, `ETH` alone are **not** valid — you must use the full pair.

To list all tradeable symbols on the testnet:

```bash
python3 -c "
from bot.client import BinanceClient
import os
from dotenv import load_dotenv
load_dotenv()
c = BinanceClient(os.getenv('BINANCE_TESTNET_API_KEY'), os.getenv('BINANCE_TESTNET_API_SECRET'))
symbols = [s['symbol'] for s in c.get_exchange_info()['symbols'] if s['status'] == 'TRADING']
print('\n'.join(symbols))
"
```

---

## Quantity Guidelines (BTCUSDT)

| Rule                      | Value           |
|---------------------------|-----------------|
| Minimum notional value    | $100 USD        |
| Safe minimum qty @ ~$95k  | 0.002 BTC       |
| Recommended test qty      | 0.002–0.01 BTC  |

---

## Assumptions

- Targets USDT-M perpetual futures only
- `timeInForce` defaults to `GTC` (Good Till Cancelled) for LIMIT orders
- All orders use one-way mode (`positionSide=BOTH`), which is the testnet default
- Quantity precision is passed as-is; Binance will reject values that violate `LOT_SIZE` filter and the error is surfaced clearly
- Credentials are loaded from `.env` via `python-dotenv`; they can also be passed as `--api-key` / `--api-secret` flags

---
#!/usr/bin/env python3
"""
Trading Bot CLI — Binance Futures Testnet
=========================================

Usage examples
--------------
# Non-interactive (single command):
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

python cli.py place --symbol BTCUSDT --side SELL --type LIMIT \
    --quantity 0.001 --price 90000

# Interactive menu:
python cli.py interactive

# Check connectivity:
python cli.py ping

# Show account balance:
python cli.py balance
"""

from __future__ import annotations
import argparse
import os
import sys
from decimal import Decimal
from dotenv import load_dotenv
from typing import Optional
from trading_bot.client import BinanceClient, BinanceAPIError
from trading_bot.logging_config import setup_logging
from trading_bot.orders import place_order
from trading_bot.validators import ValidationError, validate_all

# Colour helpers (fallback on Windows without colorama)
try:
    import colorama
    colorama.init(autoreset=True)
    GREEN  = colorama.Fore.GREEN
    RED    = colorama.Fore.RED
    YELLOW = colorama.Fore.YELLOW
    CYAN   = colorama.Fore.CYAN
    RESET  = colorama.Style.RESET_ALL
    BOLD   = colorama.Style.BRIGHT
except ImportError:
    GREEN = RED = YELLOW = CYAN = RESET = BOLD = ""


def _banner() -> None:
    print(f"""
{CYAN}{BOLD}╔══════════════════════════════════════════════╗
║    Binance Futures Testnet — Trading Bot     ║
╚══════════════════════════════════════════════╝{RESET}
""")

load_dotenv()

def _build_client(args: argparse.Namespace) -> BinanceClient:
    """Resolve API credentials from CLI flags → env vars."""
    api_key    = args.api_key    or os.getenv("BINANCE_TESTNET_API_KEY",    "")
    api_secret = args.api_secret or os.getenv("BINANCE_TESTNET_API_SECRET", "")

    if not api_key or not api_secret:
        print(
            f"{RED}✖ API credentials not found.{RESET}\n"
            "  Provide via --api-key / --api-secret flags\n"
            "  OR set env vars: BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_API_SECRET"
        )
        sys.exit(1)

    return BinanceClient(api_key=api_key, api_secret=api_secret)


# Command handlers

def cmd_ping(client: BinanceClient, _args) -> None:
    """Test connectivity to the testnet."""

    try:
        ts = client.get_server_time()
        print(f"{GREEN}✔ Connected to Binance Futures Testnet.{RESET}  Server time: {ts}")
    except Exception as exc:
        print(f"{RED}✖ Connection failed:{RESET} {exc}")
        sys.exit(1)


def cmd_balance(client: BinanceClient, _args) -> None:
    """Print USDT balance (and any non-zero assets)."""

    try:
        balances = client.get_account_balance()
    except BinanceAPIError as exc:
        print(f"{RED}✖ API error:{RESET} {exc}")
        sys.exit(1)

    print(f"\n{BOLD}Account Balances:{RESET}")
    shown = 0
    for b in balances:
        if float(b.get("balance", 0)) != 0:
            print(f"  {b['asset']:8s}  balance={b['balance']}  availableBalance={b['availableBalance']}")
            shown += 1
    if shown == 0:
        print("  (no funded assets — use testnet faucet to top up USDT)")


def cmd_place(client: BinanceClient, args) -> None:
    """Place a single order from CLI flags (non-interactive)."""

    # Print request summary
    print(f"\n{BOLD}Order Request:{RESET}")
    print(f"  Symbol    : {args.symbol}")
    print(f"  Side      : {args.side}")
    print(f"  Type      : {args.type}")
    print(f"  Quantity  : {args.quantity}")
    if args.price:
        print(f"  Price     : {args.price}")
    print()

    result = place_order(
        client=client,
        symbol=args.symbol,
        side=args.side,
        order_type=args.type,
        quantity=args.quantity,
        price=args.price,
    )

    if result.success:
        print(f"{GREEN}{result.summary()}{RESET}")
    else:
        print(f"{RED}✖ Order failed:{RESET} {result.error_message}")
        sys.exit(1)


# Interactive mode

def _prompt(text: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"  {text}{suffix}: ").strip()
    return value if value else (default or "")


def _interactive_place_order(client: BinanceClient) -> None:
    print(f"\n{CYAN}── Place New Order ──────────────────────────────{RESET}")

    symbol     = _prompt("Symbol (e.g. BTCUSDT)", "BTCUSDT").upper()
    side       = _prompt("Side   [BUY / SELL]",   "BUY").upper()
    order_type = _prompt("Type   [MARKET / LIMIT]", "MARKET").upper()
    quantity   = _prompt("Quantity")
    price: Optional[str] = None
    if order_type == "LIMIT":
        price = _prompt("Price")

    # Validate before sending
    try:
        validate_all(symbol, side, order_type, quantity, price)
    except ValidationError as exc:
        print(f"\n{YELLOW}⚠ Validation error:{RESET} {exc}")
        return

    # Confirm
    print(f"\n{BOLD}Summary:{RESET}")
    print(f"  {side} {order_type} {quantity} {symbol}" + (f" @ {price}" if price else ""))

    confirm = input(f"\n{YELLOW}Confirm? [y/N]:{RESET} ").strip().lower()
    if confirm not in ("y", "yes"):
        print("  Cancelled.")
        return

    result = place_order(client, symbol, side, order_type, quantity, price)

    if result.success:
        print(f"\n{GREEN}{result.summary()}{RESET}")
    else:
        print(f"\n{RED}✖ Order failed:{RESET} {result.error_message}")


def cmd_interactive(client: BinanceClient, _args) -> None:
    """Launch the interactive menu loop."""
    _banner()

    # Connectivity check
    try:
        client.get_server_time()
        print(f"{GREEN}✔ Connected to Binance Futures Testnet{RESET}\n")
    except Exception as exc:
        print(f"{RED}✖ Cannot connect:{RESET} {exc}")
        sys.exit(1)

    menu = {
        "1": ("Place Order",        _interactive_place_order),
        "2": ("Check Balance",      lambda c: cmd_balance(c, None)),
        "3": ("Ping / Server Time", lambda c: cmd_ping(c, None)),
        "q": ("Quit",               None),
    }

    while True:
        print(f"\n{BOLD}Main Menu:{RESET}")
        for key, (label, _) in menu.items():
            print(f"  [{key}] {label}")

        choice = input("\n  Enter choice: ").strip().lower()

        if choice == "q":
            print("  Goodbye!")
            break
        elif choice in menu:
            _, fn = menu[choice]
            if fn:
                fn(client)
        else:
            print(f"{YELLOW}  ⚠ Invalid choice. Try again.{RESET}")


# Argument parser

def build_parser() -> argparse.ArgumentParser:
    
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Global flags
    parser.add_argument("--api-key",    metavar="KEY",    help="Binance testnet API key")
    
    parser.add_argument("--api-secret", metavar="SECRET", help="Binance testnet API secret")

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # Ping
    sub.add_parser("ping", help="Test connectivity to testnet")

    # Balance
    sub.add_parser("balance", help="Show account balances")

    # Interactive
    sub.add_parser("interactive", help="Launch interactive menu")

    # Place
    place_p = sub.add_parser("place", help="Place a single order")

    place_p.add_argument("--symbol",   required=True, help="Trading pair, e.g. BTCUSDT")

    place_p.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        type=str.upper,
        help="Order side",
    )

    place_p.add_argument(
        "--type",
        required=True,
        dest="type",
        choices=["MARKET", "LIMIT"],
        type=str.upper,
        help="Order type",
    )

    place_p.add_argument("--quantity", required=True, help="Order quantity")
    place_p.add_argument("--price", default=None, help="Limit price (required for LIMIT orders)")

    return parser


# Entry point

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    logger = setup_logging(args.log_level)
    logger.debug("CLI args: %s", vars(args))

    client = _build_client(args)

    dispatch = {
        "ping":        cmd_ping,
        "balance":     cmd_balance,
        "place":       cmd_place,
        "interactive": cmd_interactive,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(client, args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

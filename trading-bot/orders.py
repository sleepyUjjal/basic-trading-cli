"""
Order orchestration layer.
Sits between the CLI and the raw BinanceClient, handling validation,
formatting, and structured result objects.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from .client import BinanceClient, BinanceAPIError
from .validators import validate_all, ValidationError

logger = logging.getLogger("trading_bot.orders")

@dataclass
class OrderResult:
    success: bool
    order_id: Optional[int] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    price: Optional[str] = None
    orig_qty: Optional[str] = None
    raw_response: dict = field(default_factory=dict)
    error_message: Optional[str] = None

    def summary(self) -> str:
        if not self.success:
            return f"[FAILED] {self.error_message}"
        lines = [
            "╔══════════════════════════════════════╗",
            "║         ORDER PLACED SUCCESSFULLY    ║",
            "╚══════════════════════════════════════╝",
            f"  Order ID     : {self.order_id}",
            f"  Symbol       : {self.symbol}",
            f"  Side         : {self.side}",
            f"  Type         : {self.order_type}",
            f"  Status       : {self.status}",
            f"  Orig Qty     : {self.orig_qty}",
            f"  Executed Qty : {self.executed_qty}",
        ]
        if self.order_type == "LIMIT":
            lines.append(f"  Limit Price  : {self.price}")
        if self.avg_price and self.avg_price != "0":
            lines.append(f"  Avg Price    : {self.avg_price}")
        return "\n".join(lines)

def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
) -> OrderResult:
    """
    Validate inputs and place an order via the client.

    Returns an OrderResult whether the order succeeded or failed,
    so the CLI layer can handle presentation uniformly.
    """
    # Validation and parameter formatting
    try:
        params = validate_all(symbol, side, order_type, quantity, price)
    except ValidationError as exc:
        logger.warning("Validation failed: %s", exc)
        return OrderResult(success=False, error_message=str(exc))

    # Log request summary
    logger.info(
        "Order request | symbol=%s side=%s type=%s qty=%s price=%s",
        params["symbol"],
        params["side"],
        params["order_type"],
        params["quantity"],
        params["price"] or "N/A (MARKET)",
    )

    # Order placement
    try:
        resp = client.place_order(
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
        )

    except ValidationError as exc:
        logger.error("Validation error during order placement: %s", exc)
        return OrderResult(success=False, error_message=str(exc))
    
    except BinanceAPIError as exc:
        logger.error("Binance API error: %s", exc)
        return OrderResult(success=False, error_message=str(exc))
    
    except (ConnectionError, TimeoutError) as exc:
        logger.error("Network error: %s", exc)
        return OrderResult(success=False, error_message=f"Network error: {exc}")

    except Exception as exc:
        logger.exception("Unexpected error placing order: %s", exc)
        return OrderResult(success=False, error_message=f"Unexpected error: {exc}")

    # Response parsing and result construction
    logger.debug("Raw order response: %s", resp)

    result = OrderResult(
        success=True,
        order_id=resp.get("orderId"),
        symbol=resp.get("symbol"),
        side=resp.get("side"),
        order_type=resp.get("type"),
        status=resp.get("status"),
        executed_qty=resp.get("executedQty"),
        avg_price=resp.get("avgPrice"),
        price=resp.get("price"),
        orig_qty=resp.get("origQty"),
        raw_response=resp,
    )

    logger.info(
        "Order result | orderId=%s status=%s executedQty=%s avgPrice=%s",
        result.order_id,
        result.status,
        result.executed_qty,
        result.avg_price,
    )

    return result
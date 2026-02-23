"""
Binance Futures Testnet REST client.
Handles authentication, request signing, and HTTP error mapping.
"""
from __future__ import annotations
import hashlib
import hmac
import logging
import time
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import urlencode
import requests

logger = logging.getLogger("trading_bot.client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW = 5000  # ms

class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, status_code: int, code: int, msg: str):
        self.status_code = status_code
        self.code = code
        self.msg = msg
        super().__init__(f"Binance API error {code}: {msg} (HTTP {status_code})")


class BinanceClient:
    """Wrapper around the Binance Futures Testnet REST API."""

    def __init__(self, api_key: str, api_secret: str, base_url: str = TESTNET_BASE_URL):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must be non-empty strings.")
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.debug("BinanceClient initialised (base_url=%s)", self._base_url)

    #internal methods

    def _sign(self, params: dict) -> dict:
        """Append a HMAC-SHA256 signature to the params dict."""

        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(self, method: str, endpoint: str, signed: bool = False, **kwargs) -> Any:
        """Execute an HTTP request and return the parsed JSON body."""

        url = f"{self._base_url}{endpoint}"
        params: dict = kwargs.pop("params", {}) or {}

        if signed:
            params = self._sign(params)

        logger.debug("→ %s %s | params=%s", method.upper(), endpoint, params)

        try:
            response = self._session.request(method, url, params=params, **kwargs)

        except requests.exceptions.ConnectionError as exc:
            logger.error("Network error contacting %s: %s", url, exc)
            raise ConnectionError(f"Cannot reach Binance testnet: {exc}") from exc
        
        except requests.exceptions.Timeout as exc:
            logger.error("Request to %s timed out: %s", url, exc)
            raise TimeoutError(f"Request timed out: {exc}") from exc

        logger.debug("← HTTP %s | body=%s", response.status_code, response.text[:500])

        # Parse JSON and handle API errors
        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response: %s", response.text[:200])
            response.raise_for_status()
            raise

        if isinstance(data, dict) and "code" in data and data["code"] != 200 and data["code"] < 0:
            raise BinanceAPIError(response.status_code, data["code"], data.get("msg", "Unknown error"))

        if not response.ok:
            raise BinanceAPIError(
                response.status_code,
                data.get("code", -1),
                data.get("msg", response.text),
            )

        return data
    
    # Public API methods

    def get_server_time(self) -> int:
        """Return server timestamp in milliseconds (connectivity check)."""

        data = self._request("GET", "/fapi/v1/time")
        return data["serverTime"]

    def get_exchange_info(self, symbol: Optional[str] = None) -> dict:
        """Return exchange info, optionally filtered to one symbol."""

        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/exchangeInfo", params=params)

    def get_account_balance(self) -> list[dict]:
        """Return futures account balance list."""

        return self._request("GET", "/fapi/v2/balance", signed=True, params={})

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> dict:
        """
        Place a new futures order.

        Parameters
        ----------
        symbol        : Trading pair, e.g. ``BTCUSDT``
        side          : ``BUY`` or ``SELL``
        order_type    : ``MARKET`` or ``LIMIT``
        quantity      : Order quantity
        price         : Required for LIMIT orders
        time_in_force : ``GTC`` (default), ``IOC``, or ``FOK``
        reduce_only   : If True, order can only reduce position
        """

        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
        }

        if order_type == "LIMIT":
            if price is None:
                raise ValueError("price is required for LIMIT orders")
            params["price"] = str(price)
            params["timeInForce"] = time_in_force

        if reduce_only:
            params["reduceOnly"] = "true"

        logger.info(
            "Placing %s %s order | symbol=%s qty=%s price=%s",
            side,
            order_type,
            symbol,
            quantity,
            price or "MARKET",
        )

        response = self._request("POST", "/fapi/v1/order", signed=True, params=params)
        logger.info("Order placed successfully | orderId=%s status=%s", response.get("orderId"), response.get("status"))

        return response

    def get_order(self, symbol: str, order_id: int) -> dict:
        """Query an existing order by ID."""

        params = {"symbol": symbol, "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", signed=True, params=params)

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an open order by ID."""
        
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("DELETE", "/fapi/v1/order", signed=True, params=params)

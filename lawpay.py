#!/usr/bin/env python3
"""
lawpay.py — LawPay payment verification integration for cmblaw.ai

This is a stub implementation that validates payment tokens and simulates
verification. Replace with actual LawPay API calls when you have credentials.

LawPay API docs: https://developer.lawpay.com/
Your payment page: https://secure.lawpay.com/pages/claytonmckayandbaileypc/operating

To activate:
1. Contact LawPay for API credentials (client_id, client_secret)
2. Set environment variables: LAWPAY_CLIENT_ID, LAWPAY_CLIENT_SECRET, LAWPAY_ENV
3. Set LAWPAY_ENABLED=true in settings
"""

import os
import json
from datetime import datetime, timezone
from typing import Optional

# Configuration
LAWPAY_CLIENT_ID = os.environ.get("LAWPAY_CLIENT_ID", "")
LAWPAY_CLIENT_SECRET = os.environ.get("LAWPAY_CLIENT_SECRET", "")
LAWPAY_ENV = os.environ.get("LAWPAY_ENV", "sandbox")  # "sandbox" or "production"
LAWPAY_BASE_URL = {
    "sandbox": "https://api.sandbox.lawpay.com/v1",
    "production": "https://api.lawpay.com/v1"
}


class PaymentResult:
    """Result of a payment verification."""
    def __init__(self, success: bool, transaction_id: str = None,
                 amount_cents: int = 0, error: str = None, raw_response: dict = None):
        self.success = success
        self.transaction_id = transaction_id
        self.amount_cents = amount_cents
        self.error = error
        self.raw_response = raw_response or {}

    def to_dict(self):
        return {
            "success": self.success,
            "transaction_id": self.transaction_id,
            "amount_cents": self.amount_cents,
            "error": self.error
        }


async def verify_payment(payment_token: str, expected_amount_cents: int,
                         description: str = "", metadata: dict = None) -> PaymentResult:
    """
    Verify a payment token with LawPay.

    In production, this would:
    1. Call LawPay's charge API with the token
    2. Verify the charge amount matches expected
    3. Return the transaction result

    Args:
        payment_token: Token from LawPay's payment form
        expected_amount_cents: Expected payment amount in cents
        description: Description for the charge (e.g., "Trademark Filing - ACME WIDGETS")
        metadata: Additional metadata to attach to the charge

    Returns:
        PaymentResult with success/failure info
    """

    # --- STUB IMPLEMENTATION ---
    # When LawPay credentials are configured, replace this with real API calls

    if LAWPAY_CLIENT_ID and LAWPAY_CLIENT_SECRET:
        # PRODUCTION: Real LawPay API call
        return await _lawpay_charge(payment_token, expected_amount_cents, description, metadata)
    else:
        # DEVELOPMENT: Simulate payment verification
        return _simulate_payment(payment_token, expected_amount_cents, description)


def _simulate_payment(token: str, amount_cents: int, description: str) -> PaymentResult:
    """Simulate payment for development/testing."""

    # Test tokens for different scenarios
    if token.startswith("tok_test_") or token.startswith("tok_live_"):
        return PaymentResult(
            success=True,
            transaction_id=f"sim_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{token[-8:]}",
            amount_cents=amount_cents,
            raw_response={"simulated": True, "description": description}
        )
    elif token == "tok_fail":
        return PaymentResult(
            success=False,
            error="Payment declined (test token)",
            raw_response={"simulated": True}
        )
    elif token == "tok_insufficient":
        return PaymentResult(
            success=False,
            error="Insufficient funds (test token)",
            raw_response={"simulated": True}
        )
    else:
        # Unknown token format — reject
        return PaymentResult(
            success=False,
            error="Invalid payment token format. Please use a valid LawPay token.",
            raw_response={"simulated": True}
        )


async def _lawpay_charge(token: str, amount_cents: int,
                         description: str, metadata: dict = None) -> PaymentResult:
    """
    Real LawPay API charge.
    TODO: Implement when LawPay API credentials are available.

    Expected flow:
    1. POST to /charges with:
       - amount: amount_cents
       - token: payment_token (from LawPay.js client-side tokenization)
       - description: service description
       - metadata: order_id, matter_id, etc.
    2. Handle response:
       - success: extract transaction_id, amount
       - failure: extract error message, decline code

    LawPay uses trust/operating account routing:
    - Earned fees (filing fees) → Operating account
    - Advance deposits → Trust account (IOLTA)

    For cmblaw.ai, all charges go to the Operating account since
    they are flat-rate fees for defined services.
    """
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{LAWPAY_BASE_URL[LAWPAY_ENV]}/charges",
                auth=(LAWPAY_CLIENT_ID, LAWPAY_CLIENT_SECRET),
                json={
                    "amount": amount_cents,
                    "token": token,
                    "description": description,
                    "reference": metadata.get("order_id", "") if metadata else "",
                    "metadata": metadata or {}
                },
                timeout=30.0
            )

            data = response.json()

            if response.status_code == 201 and data.get("status") == "authorized":
                return PaymentResult(
                    success=True,
                    transaction_id=data.get("id"),
                    amount_cents=data.get("amount", amount_cents),
                    raw_response=data
                )
            else:
                return PaymentResult(
                    success=False,
                    error=data.get("message", "Payment failed"),
                    raw_response=data
                )
    except Exception as e:
        return PaymentResult(
            success=False,
            error=f"Payment processing error: {str(e)}"
        )


async def create_refund(transaction_id: str, amount_cents: Optional[int] = None) -> PaymentResult:
    """
    Refund a charge (full or partial).
    TODO: Implement when LawPay API credentials are available.
    """
    if not LAWPAY_CLIENT_ID:
        return PaymentResult(
            success=True,
            transaction_id=f"refund_sim_{transaction_id}",
            amount_cents=amount_cents or 0,
            raw_response={"simulated": True}
        )

    # Production implementation would POST to /charges/{transaction_id}/refunds
    return PaymentResult(success=False, error="Refund not implemented for production yet")


def get_payment_page_url() -> str:
    """Get the LawPay payment page URL for manual payments."""
    return "https://secure.lawpay.com/pages/claytonmckayandbaileypc/operating"


# --- Pricing Helpers ---

SERVICE_PRICING = {
    "trademark_filing": {
        "base_cents": 20000,  # $200
        "per_class_cents": 35000,  # $350 per USPTO class
    },
    "provisional_patent": {
        "flat_cents": 150000,  # $1,500
    },
    "entity_formation": {
        "cmb_fee_cents": 15000,  # $150
        "state_fees_cents": {
            "GA": 10000, "DE": 9000, "TX": 30000, "CA": 7000,
            "NY": 20000, "FL": 12500, "IL": 15000, "NV": 7500,
        },
        "default_state_fee_cents": 10000,
    },
    "trademark_monitoring": {
        "monthly_cents": 1000,  # $10/month
    },
    "portfolio_status": {
        "flat_cents": 0,  # Free
    },
    "document_generation": {
        "flat_cents": 20000,  # $200
    },
    "consultation": {
        "flat_cents": 100,  # $1
    }
}


def calculate_price(service_type: str, **kwargs) -> int:
    """Calculate price in cents for a service. Returns amount in cents."""
    pricing = SERVICE_PRICING.get(service_type, {})

    if service_type == "trademark_filing":
        num_classes = kwargs.get("num_classes", 1)
        return pricing["base_cents"] + (pricing["per_class_cents"] * num_classes)

    elif service_type == "entity_formation":
        state = kwargs.get("state", "GA")
        state_fee = pricing["state_fees_cents"].get(state, pricing["default_state_fee_cents"])
        return pricing["cmb_fee_cents"] + state_fee

    elif service_type in ["provisional_patent", "document_generation", "consultation", "portfolio_status"]:
        return pricing.get("flat_cents", 0)

    elif service_type == "trademark_monitoring":
        return pricing["monthly_cents"]

    return 0

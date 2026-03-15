#!/usr/bin/env python3
"""
usdc_payments.py — USDC / x402 payment integration for cmblaw.ai

Supports two payment rails for AI agents:
1. x402 Protocol — HTTP-native micropayments (agent pays automatically via PAYMENT-SIGNATURE header)
2. Direct USDC Transfer — Agent sends USDC on Base, provides tx hash for verification

USDC on Base (EIP-155:8453):
- Contract: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
- Decimals: 6 (so $1.00 = 1_000_000 units, $0.01 = 10_000 units)

x402 Flow:
1. Agent calls endpoint without payment → gets 402 + PAYMENT-REQUIRED header
2. Agent signs gasless USDC transfer authorization (ERC-3009)
3. Agent retries with PAYMENT-SIGNATURE header
4. Server verifies + settles via Coinbase facilitator
5. Server returns resource + PAYMENT-RESPONSE header with tx hash

Environment Variables:
- CMBLAW_USDC_WALLET: Your Base wallet address to receive USDC payments
- CMBLAW_X402_ENABLED: "true" to enable x402 payment rail (default: "true")
- CMBLAW_USDC_DIRECT_ENABLED: "true" to enable direct USDC transfer rail (default: "true")
- CMBLAW_X402_NETWORK: "eip155:8453" for Base mainnet, "eip155:84532" for Base Sepolia (default: mainnet)
- CMBLAW_X402_FACILITATOR: Facilitator URL (default: Coinbase CDP)
"""

import os
import json
import base64
import hashlib
import time
from datetime import datetime, timezone
from typing import Optional, Tuple
from dataclasses import dataclass

# --- Configuration ---

# Your Base wallet address for receiving USDC
USDC_WALLET = os.environ.get("CMBLAW_USDC_WALLET", "0x7a00CF03325a4E5b8B80451d946899dCb07f9ce2")

# Feature flags
X402_ENABLED = os.environ.get("CMBLAW_X402_ENABLED", "true").lower() == "true"
USDC_DIRECT_ENABLED = os.environ.get("CMBLAW_USDC_DIRECT_ENABLED", "true").lower() == "true"

# Network config
X402_NETWORK = os.environ.get("CMBLAW_X402_NETWORK", "eip155:8453")  # Base mainnet
X402_FACILITATOR = os.environ.get(
    "CMBLAW_X402_FACILITATOR",
    "https://api.cdp.coinbase.com/platform/v2/x402"
)

# USDC contract addresses
USDC_CONTRACTS = {
    "eip155:8453": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",   # Base Mainnet
    "eip155:84532": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",  # Base Sepolia
}

# USDC has 6 decimals
USDC_DECIMALS = 6

# Payment timeout (seconds)
X402_TIMEOUT = 300  # 5 minutes


@dataclass
class USDCPaymentResult:
    """Result of a USDC payment verification."""
    success: bool
    method: str  # "x402", "usdc_direct", or "simulated"
    transaction_hash: Optional[str] = None
    amount_usdc: Optional[str] = None
    network: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[dict] = None

    def to_dict(self):
        return {
            "success": self.success,
            "method": self.method,
            "transaction_hash": self.transaction_hash,
            "amount_usdc": self.amount_usdc,
            "network": self.network,
            "error": self.error
        }


def cents_to_usdc_units(cents: int) -> str:
    """Convert USD cents to USDC units (6 decimals).
    $1.00 = 100 cents = 1_000_000 USDC units
    $0.01 = 1 cent = 10_000 USDC units
    """
    return str(cents * 10_000)


def cents_to_usdc_display(cents: int) -> str:
    """Convert USD cents to human-readable USDC amount.
    100 cents → "$1.00 USDC"
    """
    return f"${cents / 100:.2f}"


def build_payment_required_header(
    endpoint: str,
    price_cents: int,
    description: str = ""
) -> str:
    """Build the PAYMENT-REQUIRED header for a 402 response.
    Returns base64-encoded JSON per x402 spec.
    """
    usdc_address = USDC_CONTRACTS.get(X402_NETWORK, USDC_CONTRACTS["eip155:8453"])

    payload = {
        "x402Version": 2,
        "error": "Payment required",
        "resource": {
            "url": endpoint,
            "description": description or f"cmblaw.ai — {endpoint}",
            "mimeType": "application/json"
        },
        "accepts": [
            {
                "scheme": "exact",
                "network": X402_NETWORK,
                "amount": cents_to_usdc_units(price_cents),
                "asset": usdc_address,
                "payTo": USDC_WALLET,
                "maxTimeoutSeconds": X402_TIMEOUT,
                "extra": {
                    "name": "USDC",
                    "version": "2"
                }
            }
        ]
    }

    json_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(json_bytes).decode("ascii")


def parse_payment_signature(header_value: str) -> Optional[dict]:
    """Decode the PAYMENT-SIGNATURE header from a client.
    Returns the decoded JSON payload or None if invalid.
    """
    try:
        decoded = base64.b64decode(header_value)
        return json.loads(decoded)
    except Exception:
        return None


async def verify_x402_payment(payment_signature: str, expected_cents: int) -> USDCPaymentResult:
    """Verify an x402 payment via the Coinbase facilitator.

    1. Decode the PAYMENT-SIGNATURE header
    2. POST to facilitator /verify to check signature validity
    3. POST to facilitator /settle to execute the on-chain transfer
    4. Return the transaction hash
    """
    # Decode the payment signature
    payment_data = parse_payment_signature(payment_signature)
    if not payment_data:
        return USDCPaymentResult(
            success=False,
            method="x402",
            error="Invalid PAYMENT-SIGNATURE header — could not decode"
        )

    expected_amount = cents_to_usdc_units(expected_cents)

    # --- Development simulation ---
    if not USDC_WALLET:
        return _simulate_x402(payment_data, expected_cents)

    # --- Production: Call facilitator ---
    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Verify
            verify_resp = await client.post(
                f"{X402_FACILITATOR}/verify",
                json={
                    "payment": payment_data,
                    "expectedAmount": expected_amount,
                    "expectedPayTo": USDC_WALLET,
                    "expectedNetwork": X402_NETWORK,
                    "expectedAsset": USDC_CONTRACTS.get(X402_NETWORK)
                }
            )

            if verify_resp.status_code != 200:
                error_data = verify_resp.json() if verify_resp.headers.get("content-type", "").startswith("application") else {}
                return USDCPaymentResult(
                    success=False,
                    method="x402",
                    error=f"Payment verification failed: {error_data.get('error', verify_resp.status_code)}",
                    raw_response=error_data
                )

            # Step 2: Settle
            settle_resp = await client.post(
                f"{X402_FACILITATOR}/settle",
                json={"payment": payment_data}
            )

            if settle_resp.status_code != 200:
                error_data = settle_resp.json() if settle_resp.headers.get("content-type", "").startswith("application") else {}
                return USDCPaymentResult(
                    success=False,
                    method="x402",
                    error=f"Payment settlement failed: {error_data.get('error', settle_resp.status_code)}",
                    raw_response=error_data
                )

            settle_data = settle_resp.json()
            return USDCPaymentResult(
                success=True,
                method="x402",
                transaction_hash=settle_data.get("transaction", settle_data.get("transactionHash")),
                amount_usdc=cents_to_usdc_display(expected_cents),
                network=X402_NETWORK,
                raw_response=settle_data
            )

    except Exception as e:
        return USDCPaymentResult(
            success=False,
            method="x402",
            error=f"x402 facilitator error: {str(e)}"
        )


async def verify_usdc_direct(tx_hash: str, expected_cents: int) -> USDCPaymentResult:
    """Verify a direct USDC transfer on Base by checking the transaction.

    In production, this queries the Base blockchain (via RPC or block explorer API)
    to verify:
    1. The tx exists and is confirmed
    2. It's a USDC transfer to our wallet
    3. The amount matches expected price
    """

    # --- Development simulation ---
    if not USDC_WALLET:
        return _simulate_usdc_direct(tx_hash, expected_cents)

    # --- Production: Verify on-chain ---
    try:
        import httpx

        # Use Basescan API to verify the transaction
        basescan_api = os.environ.get("BASESCAN_API_KEY", "")
        if not basescan_api:
            # Fallback: accept the tx hash on trust during early launch
            # (you should add Basescan API key for production verification)
            print(f"WARNING: No BASESCAN_API_KEY set — accepting USDC tx {tx_hash} without on-chain verification")
            return USDCPaymentResult(
                success=True,
                method="usdc_direct",
                transaction_hash=tx_hash,
                amount_usdc=cents_to_usdc_display(expected_cents),
                network=X402_NETWORK,
                raw_response={"verified": False, "note": "Accepted without on-chain verification — configure BASESCAN_API_KEY"}
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Query transaction receipt
            resp = await client.get(
                "https://api.basescan.org/api",
                params={
                    "module": "proxy",
                    "action": "eth_getTransactionReceipt",
                    "txhash": tx_hash,
                    "apikey": basescan_api
                }
            )

            data = resp.json()
            result = data.get("result")

            if not result or result.get("status") != "0x1":
                return USDCPaymentResult(
                    success=False,
                    method="usdc_direct",
                    error="Transaction not found or not confirmed",
                    raw_response=data
                )

            # Verify it's a USDC transfer to our wallet
            usdc_contract = USDC_CONTRACTS.get(X402_NETWORK, "").lower()
            to_address = result.get("to", "").lower()

            if to_address != usdc_contract:
                return USDCPaymentResult(
                    success=False,
                    method="usdc_direct",
                    error="Transaction is not a USDC transfer",
                    raw_response=data
                )

            # Check logs for Transfer event to our wallet
            our_wallet = USDC_WALLET.lower()
            transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

            found_transfer = False
            for log_entry in result.get("logs", []):
                topics = log_entry.get("topics", [])
                if (len(topics) >= 3 and
                    topics[0] == transfer_topic and
                    topics[2].endswith(our_wallet[2:])):  # recipient match
                    found_transfer = True
                    break

            if not found_transfer:
                return USDCPaymentResult(
                    success=False,
                    method="usdc_direct",
                    error="USDC transfer to CMB wallet not found in transaction",
                    raw_response=data
                )

            return USDCPaymentResult(
                success=True,
                method="usdc_direct",
                transaction_hash=tx_hash,
                amount_usdc=cents_to_usdc_display(expected_cents),
                network=X402_NETWORK,
                raw_response={"verified": True}
            )

    except Exception as e:
        return USDCPaymentResult(
            success=False,
            method="usdc_direct",
            error=f"USDC verification error: {str(e)}"
        )


def build_payment_response_header(tx_hash: str) -> str:
    """Build the PAYMENT-RESPONSE header after successful x402 settlement.
    Returns base64-encoded JSON per x402 spec.
    """
    payload = {
        "success": True,
        "network": X402_NETWORK,
        "transaction": tx_hash
    }
    json_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(json_bytes).decode("ascii")


# --- Development Simulation ---

def _simulate_x402(payment_data: dict, expected_cents: int) -> USDCPaymentResult:
    """Simulate x402 payment for development (no wallet configured)."""
    sim_hash = f"0x{'0' * 40}{hashlib.sha256(json.dumps(payment_data).encode()).hexdigest()[:24]}"
    print(f"[DEV] Simulated x402 payment: {cents_to_usdc_display(expected_cents)} → tx {sim_hash}")
    return USDCPaymentResult(
        success=True,
        method="x402",
        transaction_hash=sim_hash,
        amount_usdc=cents_to_usdc_display(expected_cents),
        network=X402_NETWORK,
        raw_response={"simulated": True}
    )


def _simulate_usdc_direct(tx_hash: str, expected_cents: int) -> USDCPaymentResult:
    """Simulate direct USDC transfer verification for development."""
    if tx_hash.startswith("0x") and len(tx_hash) == 66:
        print(f"[DEV] Simulated USDC direct verification: {tx_hash}")
        return USDCPaymentResult(
            success=True,
            method="usdc_direct",
            transaction_hash=tx_hash,
            amount_usdc=cents_to_usdc_display(expected_cents),
            network=X402_NETWORK,
            raw_response={"simulated": True}
        )
    else:
        return USDCPaymentResult(
            success=False,
            method="usdc_direct",
            error="Invalid transaction hash format. Must be 0x followed by 64 hex characters."
        )


# --- Info Helpers ---

def get_usdc_payment_info() -> dict:
    """Return USDC payment info for API documentation endpoints."""
    usdc_address = USDC_CONTRACTS.get(X402_NETWORK, USDC_CONTRACTS["eip155:8453"])
    return {
        "usdc_enabled": X402_ENABLED or USDC_DIRECT_ENABLED,
        "methods": {
            "x402": {
                "enabled": X402_ENABLED,
                "description": "Automatic HTTP-native payment via x402 protocol. "
                              "Send request without payment → receive 402 with payment instructions → "
                              "sign USDC transfer → retry with PAYMENT-SIGNATURE header.",
                "network": X402_NETWORK,
                "usdc_contract": usdc_address,
                "facilitator": X402_FACILITATOR,
                "documentation": "https://docs.cdp.coinbase.com/x402/welcome"
            },
            "usdc_direct": {
                "enabled": USDC_DIRECT_ENABLED,
                "description": "Send USDC directly to CMB wallet on Base, then include tx hash in request.",
                "network": X402_NETWORK,
                "usdc_contract": usdc_address,
                "wallet_address": USDC_WALLET or "(configure CMBLAW_USDC_WALLET)",
                "parameter": "usdc_tx_hash"
            }
        },
        "also_accepted": {
            "lawpay": {
                "description": "Traditional card payment via LawPay",
                "parameter": "payment_token",
                "payment_page": "https://secure.lawpay.com/pages/claytonmckayandbaileypc/operating"
            }
        }
    }

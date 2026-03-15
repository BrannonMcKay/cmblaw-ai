#!/usr/bin/env python3
"""
api_server.py — cmblaw.ai hardened backend API server (port 8001)

Security features:
- HMAC-SHA256 hashed API keys in SQLite (never stored in plaintext)
- Persistent rate limiting (DB-backed, survives restarts)
- Multi-signal abuse detection (per-key + per-IP correlation)
- Tamper-evident audit logging with hash chains
- Strict input validation and sanitization on all fields
- URL validation for file references
- Payment verification gate (LawPay integration)
- IP tracking and blocking
- Global kill switch
- Separate admin authentication
- Data retention and purge policies
- Request size limits
"""

import json
import uuid
import os
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import (
    init_db, seed_demo_data, get_db, hash_api_key,
    log_audit_event, check_rate_limit, check_abuse,
    get_setting, set_setting, purge_expired_data,
    generate_api_key, generate_admin_key
)
from notifications import (
    notify_attorneys_new_submission,
    notify_attorney_consultation_message,
    send_client_confirmation,
    fire_consultation_reply_webhook,
    fire_status_update_webhook
)
from validation import (
    TrademarkFilingRequest, ProvisionalPatentRequest,
    EntityFormationRequest,
    DocumentGenerateRequest, ConsultationBookRequest,
    ConsultationMessageRequest,
    sanitize_text
)
from lawpay import verify_payment, calculate_price, get_payment_page_url
from usdc_payments import (
    X402_ENABLED, USDC_DIRECT_ENABLED,
    build_payment_required_header, build_payment_response_header,
    verify_x402_payment, verify_usdc_direct,
    cents_to_usdc_display, get_usdc_payment_info
)


# --- Constants ---
MAX_REQUEST_SIZE = 1_048_576  # 1MB max request body
ATTORNEY_EMAILS = {
    "brannon": "brannon@cmblaw.com",
    "josh": "josh@cmblaw.com",
    "ben": "ben@cmblaw.com",
    "ginger": "ginger@cmblaw.com",
    "manoj": "manoj@cmblaw.com",
    "becky": "becky@cmblaw.com",
    "info": "info@cmblaw.com"
}


# --- Lifespan ---
@asynccontextmanager
async def lifespan(app):
    print("cmblaw.ai API server starting — initializing database...")
    init_db()
    seed_demo_data()
    print("cmblaw.ai API server ready on port 8001")
    yield
    print("cmblaw.ai API server shutting down")


# --- App Setup ---
app = FastAPI(
    title="cmblaw.ai API",
    description="AI Agent Access to Elite Human Attorneys — by Clayton, McKay & Bailey, PC",
    version="1.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


# --- Middleware: Request Size Limit ---
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE:
        return JSONResponse(
            status_code=413,
            content={"error": "request_too_large", "message": f"Request body exceeds {MAX_REQUEST_SIZE // 1024}KB limit"}
        )
    return await call_next(request)


# --- Auth Dependencies ---

def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def validate_api_key(request: Request, x_api_key: str = Header(None)):
    """Validate API key, check rate limits and abuse."""
    conn = get_db()
    ip = get_client_ip(request)
    endpoint = request.url.path

    try:
        # Kill switch check
        if get_setting(conn, "intake_enabled") != "true":
            log_audit_event(conn, "REQUEST_BLOCKED_KILLSWITCH", "api_key", "unknown",
                           ip_address=ip, endpoint=endpoint, method=request.method,
                           response_status=503)
            raise HTTPException(status_code=503, detail={
                "error": "service_paused",
                "message": "API intake is temporarily paused. Please try again later."
            })

        # API key required
        if not x_api_key:
            log_audit_event(conn, "AUTH_MISSING", "anonymous", ip_address=ip,
                           endpoint=endpoint, method=request.method, response_status=401)
            raise HTTPException(status_code=401, detail={
                "error": "authentication_required",
                "message": "Missing X-API-Key header. Request a key at info@cmblaw.com"
            })

        # Look up key
        key_hash = hash_api_key(x_api_key)
        key_row = conn.execute(
            "SELECT * FROM api_keys WHERE key_hash=?", (key_hash,)
        ).fetchone()

        if not key_row:
            log_audit_event(conn, "AUTH_INVALID_KEY", "anonymous", ip_address=ip,
                           endpoint=endpoint, method=request.method, response_status=401,
                           details=f"Key prefix: {x_api_key[:12]}...")
            raise HTTPException(status_code=401, detail={
                "error": "invalid_api_key",
                "message": "Invalid API key."
            })

        if not key_row["active"]:
            log_audit_event(conn, "AUTH_REVOKED_KEY", "api_key", str(key_row["id"]),
                           ip_address=ip, endpoint=endpoint, method=request.method, response_status=401)
            raise HTTPException(status_code=401, detail={
                "error": "revoked_api_key",
                "message": f"API key has been revoked. Reason: {key_row['revoke_reason'] or 'Contact info@cmblaw.com'}"
            })

        # IP restriction check
        if key_row["allowed_ips"]:
            allowed = json.loads(key_row["allowed_ips"])
            if ip not in allowed:
                log_audit_event(conn, "AUTH_IP_REJECTED", "api_key", str(key_row["id"]),
                               ip_address=ip, endpoint=endpoint, method=request.method,
                               response_status=403, details=f"IP {ip} not in allowlist")
                raise HTTPException(status_code=403, detail={
                    "error": "ip_not_allowed",
                    "message": "Request from unauthorized IP address."
                })

        # Abuse detection
        allowed, reason = check_abuse(conn, key_row["id"], ip)
        if not allowed:
            log_audit_event(conn, "ABUSE_BLOCKED", "api_key", str(key_row["id"]),
                           ip_address=ip, endpoint=endpoint, method=request.method,
                           response_status=429, details=reason)
            raise HTTPException(status_code=429, detail={
                "error": "abuse_detected",
                "message": reason
            })

        # Rate limiting
        rate_allowed, limits = check_rate_limit(conn, key_row["id"], ip, endpoint)
        if not rate_allowed:
            log_audit_event(conn, "RATE_LIMITED", "api_key", str(key_row["id"]),
                           ip_address=ip, endpoint=endpoint, method=request.method,
                           response_status=429)
            raise HTTPException(status_code=429, detail={
                "error": "rate_limited",
                "message": "Rate limit exceeded",
                "retry_after": 3600,
                "limits": limits
            })

        # Update last used
        conn.execute("UPDATE api_keys SET last_used_at=? WHERE id=?",
                     (datetime.now(timezone.utc).isoformat(), key_row["id"]))
        conn.commit()

        return {
            "key_id": key_row["id"],
            "org": key_row["org_name"],
            "email": key_row["org_email"],
            "scopes": json.loads(key_row["scopes"]),
            "limits": limits,
            "ip": ip
        }

    finally:
        conn.close()


async def validate_admin_key(request: Request, x_api_key: str = Header(None)):
    """Validate admin authentication."""
    conn = get_db()
    ip = get_client_ip(request)

    try:
        if not x_api_key:
            raise HTTPException(status_code=401, detail={"error": "admin_auth_required"})

        key_hash = hash_api_key(x_api_key)
        admin_row = conn.execute(
            "SELECT * FROM admin_keys WHERE key_hash=? AND active=1", (key_hash,)
        ).fetchone()

        if not admin_row:
            log_audit_event(conn, "ADMIN_AUTH_FAILED", "anonymous", ip_address=ip,
                           endpoint=request.url.path, method=request.method, response_status=403)
            raise HTTPException(status_code=403, detail={"error": "invalid_admin_key"})

        conn.execute("UPDATE admin_keys SET last_used_at=? WHERE id=?",
                     (datetime.now(timezone.utc).isoformat(), admin_row["id"]))
        conn.commit()

        log_audit_event(conn, "ADMIN_AUTH_SUCCESS", "admin", str(admin_row["id"]),
                       ip_address=ip, endpoint=request.url.path, method=request.method)

        return {"admin_id": admin_row["id"], "name": admin_row["admin_name"], "ip": ip}

    finally:
        conn.close()


# --- Helpers ---

def generate_order_id():
    return f"CMB-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

def generate_matter_id():
    return f"M-{uuid.uuid4().hex[:10].upper()}"

def add_rate_limit_headers(response, limits):
    response.headers["X-RateLimit-Hourly-Limit"] = str(limits["hourly"]["limit"])
    response.headers["X-RateLimit-Hourly-Remaining"] = str(limits["hourly"]["remaining"])
    response.headers["X-RateLimit-Daily-Limit"] = str(limits["daily"]["limit"])
    response.headers["X-RateLimit-Daily-Remaining"] = str(limits["daily"]["remaining"])
    return response

def calculate_purge_date(conn) -> str:
    """Calculate the purge date based on retention settings."""
    days = int(get_setting(conn, "data_retention_days") or 2555)
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


# --- AI Conflict Checking ---


async def resolve_payment(
    request: Request,
    payment_token: str = None,
    usdc_tx_hash: str = None,
    price_cents: int = 0,
    service_name: str = "",
    endpoint: str = ""
) -> dict:
    """Unified payment resolution across all three rails.

    Priority:
    1. x402 (PAYMENT-SIGNATURE header) — native agent micropayment
    2. USDC direct transfer (usdc_tx_hash field) — agent sends USDC on Base
    3. LawPay token (payment_token field) — traditional card payment

    Returns dict with: success, method, transaction_id, error, response_headers
    If no payment method provided and x402 is enabled, returns 402 with payment instructions.
    """
    result = {
        "success": False,
        "method": None,
        "transaction_id": None,
        "error": None,
        "response_headers": {}  # extra headers to add to response (e.g. PAYMENT-RESPONSE)
    }

    # --- Rail 1: x402 Protocol (check for PAYMENT-SIGNATURE header) ---
    payment_sig = request.headers.get("payment-signature")
    if payment_sig and X402_ENABLED:
        usdc_result = await verify_x402_payment(payment_sig, price_cents)
        if usdc_result.success:
            result["success"] = True
            result["method"] = "x402"
            result["transaction_id"] = usdc_result.transaction_hash
            result["response_headers"]["PAYMENT-RESPONSE"] = build_payment_response_header(
                usdc_result.transaction_hash
            )
            return result
        else:
            result["error"] = usdc_result.error
            return result

    # --- Rail 2: Direct USDC transfer (usdc_tx_hash in request body) ---
    if usdc_tx_hash and USDC_DIRECT_ENABLED:
        usdc_result = await verify_usdc_direct(usdc_tx_hash, price_cents)
        if usdc_result.success:
            result["success"] = True
            result["method"] = "usdc_direct"
            result["transaction_id"] = usdc_result.transaction_hash
            return result
        else:
            result["error"] = usdc_result.error
            return result

    # --- Rail 3: LawPay token (traditional card payment) ---
    if payment_token:
        lawpay_result = await verify_payment(
            payment_token, price_cents,
            description=service_name,
            metadata={"service": service_name}
        )
        if lawpay_result.success:
            result["success"] = True
            result["method"] = "lawpay"
            result["transaction_id"] = lawpay_result.transaction_id
            return result
        else:
            result["error"] = lawpay_result.error
            return result

    # --- No payment method provided → return 402 with x402 instructions ---
    if X402_ENABLED:
        result["error"] = "x402_payment_required"
        result["response_headers"]["PAYMENT-REQUIRED"] = build_payment_required_header(
            endpoint=endpoint,
            price_cents=price_cents,
            description=service_name
        )
        return result

    # No payment at all and x402 not enabled
    result["error"] = (
        "Payment required. Provide payment_token (LawPay) or usdc_tx_hash (USDC on Base). "
        "See GET /api/v1/payment-methods for details."
    )
    return result


async def run_conflict_check(mark_text: str = None, description: str = None, check_type: str = "trademark"):
    """Run AI-powered conflict check using Claude. Used for trademark conflict analysis."""
    try:
        from anthropic import Anthropic
        client = Anthropic()

        prompt = f"""You are an AI assistant helping with trademark conflict analysis for a law firm.

Analyze the following proposed trademark for potential conflicts:

Mark: {sanitize_text(mark_text or '', 500)}

Consider:
1. Phonetic similarity to well-known marks
2. Visual similarity
3. Likelihood of confusion in the relevant market
4. Descriptiveness concerns
5. Generic term concerns

Provide a brief conflict risk assessment with:
- risk_level: "low", "moderate", or "high"
- summary: 2-3 sentence assessment
- flags: array of specific concerns (empty if none)

Respond in valid JSON only."""

        message = client.messages.create(
            model="claude_haiku_4_5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        return json.loads(response_text)
    except Exception as e:
        print(f"Conflict check error: {e}")
        return {
            "risk_level": "pending",
            "summary": "Automated conflict check is being processed. An attorney will review manually.",
            "flags": []
        }


# --- API Endpoints ---

@app.get("/api/health")
async def health_check():
    conn = get_db()
    try:
        intake = get_setting(conn, "intake_enabled")
        return {
            "status": "healthy",
            "service": "cmblaw.ai",
            "version": "1.2.0",
            "intake_enabled": intake == "true",
            "payment_rails": {
                "x402": X402_ENABLED,
                "usdc_direct": USDC_DIRECT_ENABLED,
                "lawpay": True
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    finally:
        conn.close()


@app.get("/api/v1/payment-methods")
async def get_payment_methods():
    """Returns available payment methods and how to use each one.
    AI agents should prefer x402 (automatic) or USDC direct transfer."""
    return get_usdc_payment_info()


# --- 1. Trademark Filing ---
@app.post("/api/v1/trademark/file")
async def file_trademark(req: TrademarkFilingRequest, request: Request, auth: dict = Depends(validate_api_key)):
    conn = get_db()
    try:
        # Calculate pricing
        num_classes = len(req.uspto_classes)
        price_cents = calculate_price("trademark_filing", num_classes=num_classes)

        # Resolve payment (x402 → USDC direct → LawPay)
        payment = await resolve_payment(
            request=request,
            payment_token=req.payment_token,
            usdc_tx_hash=req.usdc_tx_hash,
            price_cents=price_cents,
            service_name=f"Trademark Filing - {req.mark_text}",
            endpoint="/api/v1/trademark/file"
        )

        if not payment["success"]:
            # x402: return 402 with payment instructions header
            if payment["error"] == "x402_payment_required":
                return JSONResponse(
                    status_code=402,
                    content={"error": "payment_required", "message": "Payment required. Use x402, USDC transfer, or LawPay token.",
                             "price": cents_to_usdc_display(price_cents), "payment_methods": "/api/v1/payment-methods"},
                    headers=payment["response_headers"]
                )
            log_audit_event(conn, "PAYMENT_FAILED", "api_key", str(auth["key_id"]),
                           ip_address=auth["ip"], endpoint="/api/v1/trademark/file",
                           method="POST", response_status=402,
                           details=f"Payment failed: {payment['error']}")
            raise HTTPException(status_code=402, detail={
                "error": "payment_failed",
                "message": payment["error"],
                "payment_methods": "/api/v1/payment-methods"
            })

        # Run AI conflict check
        conflict_result = await run_conflict_check(mark_text=req.mark_text, check_type="trademark")

        order_id = generate_order_id()
        matter_id = generate_matter_id()

        # Store submission
        conn.execute("""
            INSERT INTO submissions (order_id, matter_id, submission_type, status, api_key_id,
                                    org_name, request_data, conflict_check_result, pricing,
                                    payment_token, payment_verified, payment_verified_at,
                                    ip_address, user_agent, created_at, updated_at, purge_after)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_id, matter_id, "trademark_filing", "pending_review", auth["key_id"],
              auth["org"], json.dumps(req.model_dump()), json.dumps(conflict_result),
              json.dumps({"base_cents": 20000, "per_class_cents": 35000, "num_classes": num_classes, "total_cents": price_cents}),
              payment["transaction_id"], 1, datetime.now(timezone.utc).isoformat(),
              auth["ip"], request.headers.get("user-agent", ""),
              datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(),
              calculate_purge_date(conn)))
        conn.commit()

        log_audit_event(conn, "SUBMISSION_CREATED", "api_key", str(auth["key_id"]),
                       ip_address=auth["ip"], endpoint="/api/v1/trademark/file",
                       method="POST", response_status=201,
                       request_summary=f"Trademark: {req.mark_text}, Classes: {req.uspto_classes}",
                       details=json.dumps({"order_id": order_id, "matter_id": matter_id, "price_cents": price_cents}))

        total_dollars = price_cents / 100
        response_data = {
            "order_id": order_id,
            "matter_id": matter_id,
            "status": "pending_review",
            "pricing": {
                "base_fee": "$200.00",
                "class_fees": f"${350 * num_classes:.2f} ({num_classes} class{'es' if num_classes > 1 else ''})",
                "total": f"${total_dollars:.2f}"
            },
            "payment": {"verified": True, "transaction_id": payment["transaction_id"], "method": payment["method"]},
            "estimated_timeline": "7-10 business days",
            "conflict_check_summary": conflict_result,
            "next_steps": "Your submission is being reviewed by attorney Brannon McKay. You will receive confirmation at your contact email."
        }

        response = JSONResponse(content=response_data, status_code=201)

        # Add x402 payment response header if applicable
        for hdr, val in payment["response_headers"].items():
            response.headers[hdr] = val

        # Fire notifications (non-blocking)
        try:
            notify_attorneys_new_submission(
                submission_type="trademark_filing",
                order_id=order_id,
                org_name=auth["org"],
                request_summary=f"Mark: {req.mark_text}, Classes: {req.uspto_classes}, Basis: {req.filing_basis}",
                pricing={"Total": f"${total_dollars:.2f}", "Classes": str(num_classes)}
            )
            send_client_confirmation(
                to_email=req.contact_email,
                submission_type="trademark_filing",
                order_id=order_id,
                matter_id=matter_id,
                pricing={"CMB Fee": "$200.00", "Class Fees": f"${350 * num_classes:.2f}", "Total": f"${total_dollars:.2f}"},
                timeline="7-10 business days",
                next_steps="Your submission is being reviewed by a CMB attorney. You will receive an update when the trademark application is filed."
            )
        except Exception as e:
            print(f"Notification error (trademark): {e}")

        return add_rate_limit_headers(response, auth["limits"])

    finally:
        conn.close()


# --- 2. Provisional Patent ---
@app.post("/api/v1/patent/provisional")
async def file_provisional_patent(req: ProvisionalPatentRequest, request: Request, auth: dict = Depends(validate_api_key)):
    conn = get_db()
    try:
        price_cents = calculate_price("provisional_patent")

        # Resolve payment (x402 → USDC direct → LawPay)
        payment = await resolve_payment(
            request=request,
            payment_token=req.payment_token,
            usdc_tx_hash=req.usdc_tx_hash,
            price_cents=price_cents,
            service_name="U.S. Provisional Patent Application",
            endpoint="/api/v1/patent/provisional"
        )

        if not payment["success"]:
            if payment["error"] == "x402_payment_required":
                return JSONResponse(
                    status_code=402,
                    content={"error": "payment_required", "message": "Payment required.",
                             "price": cents_to_usdc_display(price_cents), "payment_methods": "/api/v1/payment-methods"},
                    headers=payment["response_headers"]
                )
            log_audit_event(conn, "PAYMENT_FAILED", "api_key", str(auth["key_id"]),
                           ip_address=auth["ip"], endpoint="/api/v1/patent/provisional",
                           method="POST", response_status=402,
                           details=f"Payment failed: {payment['error']}")
            raise HTTPException(status_code=402, detail={
                "error": "payment_failed", "message": payment["error"],
                "payment_methods": "/api/v1/payment-methods"
            })

        order_id = generate_order_id()
        matter_id = generate_matter_id()

        conn.execute("""
            INSERT INTO submissions (order_id, matter_id, submission_type, status, api_key_id,
                                    org_name, request_data, conflict_check_result, pricing,
                                    payment_token, payment_verified, payment_verified_at,
                                    ip_address, user_agent, created_at, updated_at, purge_after)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_id, matter_id, "provisional_patent", "pending_review", auth["key_id"],
              auth["org"], json.dumps(req.model_dump()), json.dumps({"note": "No prior art analysis — AI-assisted drafting with attorney review"}),
              json.dumps({"cmb_fee_cents": price_cents, "note": "USPTO filing fee ($130 small entity) is separate"}),
              payment["transaction_id"], 1, datetime.now(timezone.utc).isoformat(),
              auth["ip"], request.headers.get("user-agent", ""),
              datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(),
              calculate_purge_date(conn)))
        conn.commit()

        log_audit_event(conn, "SUBMISSION_CREATED", "api_key", str(auth["key_id"]),
                       ip_address=auth["ip"], endpoint="/api/v1/patent/provisional",
                       method="POST", response_status=201,
                       request_summary="Provisional patent application",
                       details=json.dumps({"order_id": order_id, "matter_id": matter_id}))

        response_data = {
            "order_id": order_id, "matter_id": matter_id,
            "status": "pending_review",
            "pricing": {"cmb_fee": "$1,500.00", "uspto_fee": "$130.00 (small entity, billed separately)"},
            "payment": {"verified": True, "transaction_id": payment["transaction_id"], "method": payment["method"]},
            "estimated_timeline": "14-21 business days",
            "drafting": {
                "method": "ai_assisted",
                "review": "attorney",
                "details": "AI-assisted draft in progress — attorney will review, refine, and finalize before filing"
            },
            "next_steps": "Your provisional patent application is being prepared using AI-assisted drafting. Attorney Brannon McKay will review, refine, and finalize the application. You will receive a draft for review before filing."
        }

        response = JSONResponse(content=response_data, status_code=201)

        # Add x402 payment response header if applicable
        for hdr, val in payment["response_headers"].items():
            response.headers[hdr] = val

        # Fire notifications
        try:
            notify_attorneys_new_submission(
                submission_type="provisional_patent",
                order_id=order_id,
                org_name=auth["org"],
                request_summary=f"Provisional patent application submitted",
                pricing={"CMB Fee": "$1,500.00", "USPTO Fee": "$130.00 (separate)"}
            )
            send_client_confirmation(
                to_email=req.contact_email,
                submission_type="provisional_patent",
                order_id=order_id,
                matter_id=matter_id,
                pricing={"CMB Fee": "$1,500.00", "USPTO Fee": "$130.00 (small entity, billed separately)"},
                timeline="14-21 business days",
                next_steps="AI-assisted drafting is in progress. An attorney will review, refine, and finalize the application. You will receive a draft for review before filing."
            )
        except Exception as e:
            print(f"Notification error (patent): {e}")

        return add_rate_limit_headers(response, auth["limits"])
    finally:
        conn.close()


# --- 3. Entity Formation ---
@app.post("/api/v1/entity/form")
async def form_entity(req: EntityFormationRequest, request: Request, auth: dict = Depends(validate_api_key)):
    conn = get_db()
    try:
        price_cents = calculate_price("entity_formation", state=req.state)

        # Resolve payment (x402 → USDC direct → LawPay)
        payment = await resolve_payment(
            request=request,
            payment_token=req.payment_token,
            usdc_tx_hash=req.usdc_tx_hash,
            price_cents=price_cents,
            service_name=f"Entity Formation - {req.entity_name} ({req.entity_type}, {req.state})",
            endpoint="/api/v1/entity/form"
        )

        if not payment["success"]:
            if payment["error"] == "x402_payment_required":
                return JSONResponse(
                    status_code=402,
                    content={"error": "payment_required", "message": "Payment required.",
                             "price": cents_to_usdc_display(price_cents), "payment_methods": "/api/v1/payment-methods"},
                    headers=payment["response_headers"]
                )
            raise HTTPException(status_code=402, detail={
                "error": "payment_failed", "message": payment["error"],
                "payment_methods": "/api/v1/payment-methods"
            })

        order_id = generate_order_id()
        from lawpay import SERVICE_PRICING
        state_fee_cents = SERVICE_PRICING["entity_formation"]["state_fees_cents"].get(req.state, 10000)
        cmb_fee_cents = SERVICE_PRICING["entity_formation"]["cmb_fee_cents"]

        conn.execute("""
            INSERT INTO submissions (order_id, submission_type, status, api_key_id,
                                    org_name, request_data, pricing,
                                    payment_token, payment_verified, payment_verified_at,
                                    ip_address, user_agent, created_at, updated_at, purge_after)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_id, "entity_formation", "processing", auth["key_id"],
              auth["org"], json.dumps(req.model_dump()),
              json.dumps({"state_fee_cents": state_fee_cents, "cmb_fee_cents": cmb_fee_cents, "total_cents": price_cents}),
              payment["transaction_id"], 1, datetime.now(timezone.utc).isoformat(),
              auth["ip"], request.headers.get("user-agent", ""),
              datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(),
              calculate_purge_date(conn)))
        conn.commit()

        log_audit_event(conn, "SUBMISSION_CREATED", "api_key", str(auth["key_id"]),
                       ip_address=auth["ip"], endpoint="/api/v1/entity/form",
                       method="POST", response_status=201,
                       request_summary=f"Entity formation: {req.entity_name} ({req.entity_type})")

        response_data = {
            "order_id": order_id, "status": "processing",
            "entity_type": req.entity_type, "entity_name": req.entity_name, "state": req.state,
            "pricing": {
                "state_filing_fee": f"${state_fee_cents/100:.2f}",
                "cmb_fee": "$150.00",
                "total": f"${price_cents/100:.2f}"
            },
            "payment": {"verified": True, "transaction_id": payment["transaction_id"], "method": payment["method"]},
            "estimated_completion": "3-5 business days",
            "includes": ["Entity filing", "Registered agent (first year)", "EIN application", "Operating agreement template"],
            "next_steps": f"Filing with {req.state} Secretary of State will begin immediately."
        }

        response = JSONResponse(content=response_data, status_code=201)

        # Add x402 payment response header if applicable
        for hdr, val in payment["response_headers"].items():
            response.headers[hdr] = val

        # Fire notifications
        try:
            notify_attorneys_new_submission(
                submission_type="entity_formation",
                order_id=order_id,
                org_name=auth["org"],
                request_summary=f"{req.entity_type}: {req.entity_name} in {req.state}",
                pricing={"Total": f"${price_cents/100:.2f}"}
            )
            send_client_confirmation(
                to_email=req.contact_email,
                submission_type="entity_formation",
                order_id=order_id,
                pricing={"State Filing Fee": f"${state_fee_cents/100:.2f}", "CMB Fee": "$150.00", "Total": f"${price_cents/100:.2f}"},
                timeline="3-5 business days",
                next_steps=f"Filing with {req.state} Secretary of State will begin immediately."
            )
        except Exception as e:
            print(f"Notification error (entity): {e}")

        return add_rate_limit_headers(response, auth["limits"])
    finally:
        conn.close()


# --- 4. Trademark Monitor (DEPRECATED — replaced with free toolkit on frontend) ---
# The monitoring endpoint has been replaced with a free Trademark Monitoring Toolkit
# that empowers AI agents to monitor trademarks themselves using USPTO TSDR API,
# conflict search strategies, and escalation criteria. Agents escalate to CMB
# via consultation ($1) or trademark filing ($200) when issues are detected.
#
# @app.post("/api/v1/trademark/monitor")
# async def start_trademark_monitoring(...):
#     [endpoint code preserved in git history]


# --- 5. Portfolio Status (Free) ---
@app.get("/api/v1/portfolio/status")
async def get_portfolio_status(request: Request, matter_id: str = None, auth: dict = Depends(validate_api_key)):
    conn = get_db()
    try:
        query = "SELECT * FROM submissions WHERE api_key_id=?"
        params = [auth["key_id"]]

        if matter_id:
            matter_id = sanitize_text(matter_id, 50)
            query += " AND (matter_id=? OR order_id=?)"
            params.extend([matter_id, matter_id])

        rows = conn.execute(query + " ORDER BY created_at DESC", params).fetchall()

        matters = []
        for row in rows:
            matter = {
                "matter_id": row["matter_id"] or row["order_id"],
                "order_id": row["order_id"],
                "type": row["submission_type"],
                "status": row["status"],
                "submitted_at": row["created_at"],
                "payment_verified": bool(row["payment_verified"]),
                "deadlines": [],
                "next_actions": []
            }

            data = json.loads(row["request_data"]) if row["request_data"] else {}

            if row["submission_type"] == "trademark_filing":
                matter["mark_text"] = data.get("mark_text")
                matter["deadlines"] = [
                    {"description": "Attorney review", "due_date": "Pending"},
                    {"description": "USPTO filing", "due_date": "TBD after review"}
                ]
            elif row["submission_type"] == "provisional_patent":
                matter["deadlines"] = [
                    {"description": "Draft preparation", "due_date": "Pending"},
                    {"description": "Client review", "due_date": "TBD"},
                    {"description": "USPTO filing", "due_date": "TBD"}
                ]
            elif row["submission_type"] == "entity_formation":
                matter["entity_name"] = data.get("entity_name")

            matters.append(matter)

        log_audit_event(conn, "PORTFOLIO_QUERY", "api_key", str(auth["key_id"]),
                       ip_address=auth["ip"], endpoint="/api/v1/portfolio/status",
                       method="GET", response_status=200,
                       details=f"Returned {len(matters)} matters")

        response_data = {
            "org": auth["org"],
            "total_matters": len(matters),
            "matters": matters,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }

        response = JSONResponse(content=response_data)
        return add_rate_limit_headers(response, auth["limits"])
    finally:
        conn.close()


# --- 6. Document Generation ---
@app.post("/api/v1/documents/generate")
async def generate_document(req: DocumentGenerateRequest, request: Request, auth: dict = Depends(validate_api_key)):
    conn = get_db()
    try:
        price_cents = calculate_price("document_generation")

        # Resolve payment (x402 → USDC direct → LawPay)
        payment = await resolve_payment(
            request=request,
            payment_token=req.payment_token,
            usdc_tx_hash=req.usdc_tx_hash,
            price_cents=price_cents,
            service_name=f"Document Generation - {req.document_type}",
            endpoint="/api/v1/documents/generate"
        )

        if not payment["success"]:
            if payment["error"] == "x402_payment_required":
                return JSONResponse(
                    status_code=402,
                    content={"error": "payment_required", "message": "Payment required.",
                             "price": cents_to_usdc_display(price_cents), "payment_methods": "/api/v1/payment-methods"},
                    headers=payment["response_headers"]
                )
            raise HTTPException(status_code=402, detail={
                "error": "payment_failed", "message": payment["error"],
                "payment_methods": "/api/v1/payment-methods"
            })

        order_id = generate_order_id()

        conn.execute("""
            INSERT INTO submissions (order_id, submission_type, status, api_key_id,
                                    org_name, request_data, pricing,
                                    payment_token, payment_verified, payment_verified_at,
                                    ip_address, user_agent, created_at, updated_at, purge_after)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_id, "document_generation", "pending_review", auth["key_id"],
              auth["org"], json.dumps(req.model_dump()),
              json.dumps({"flat_cents": price_cents}),
              payment["transaction_id"], 1, datetime.now(timezone.utc).isoformat(),
              auth["ip"], request.headers.get("user-agent", ""),
              datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(),
              calculate_purge_date(conn)))
        conn.commit()

        log_audit_event(conn, "SUBMISSION_CREATED", "api_key", str(auth["key_id"]),
                       ip_address=auth["ip"], endpoint="/api/v1/documents/generate",
                       method="POST", response_status=201,
                       request_summary=f"Document: {req.document_type}")

        response_data = {
            "order_id": order_id, "document_type": req.document_type,
            "status": "pending_review",
            "parties": [p.get("name", "Unknown") for p in req.parties],
            "pricing": {"total": "$200.00"},
            "payment": {"verified": True, "transaction_id": payment["transaction_id"], "method": payment["method"]},
            "estimated_delivery": "1-2 business days",
            "next_steps": "Document will be AI-generated from vetted templates, then reviewed by an attorney before delivery."
        }

        response = JSONResponse(content=response_data, status_code=201)

        # Add x402 payment response header
        for hdr, val in payment["response_headers"].items():
            response.headers[hdr] = val

        # Fire notifications
        try:
            party_names = [p.get("name", "Unknown") for p in req.parties]
            notify_attorneys_new_submission(
                submission_type="document_generation",
                order_id=order_id,
                org_name=auth["org"],
                request_summary=f"{req.document_type} for {', '.join(party_names)}",
                pricing={"Total": "$200.00"}
            )
            send_client_confirmation(
                to_email=req.contact_email,
                submission_type="document_generation",
                order_id=order_id,
                pricing={"Total": "$200.00"},
                timeline="1-2 business days",
                next_steps="Document will be AI-generated from vetted templates, then reviewed by an attorney before delivery."
            )
        except Exception as e:
            print(f"Notification error (document): {e}")

        return add_rate_limit_headers(response, auth["limits"])
    finally:
        conn.close()


# --- 7. Consultation — Open Async Thread ---
@app.post("/api/v1/consultation/book")
async def open_consultation(req: ConsultationBookRequest, request: Request, auth: dict = Depends(validate_api_key)):
    """Open an async consultation thread with a CMB attorney.
    Returns a consultation_id used to exchange messages."""
    conn = get_db()
    try:
        price_cents = calculate_price("consultation")

        # Resolve payment (x402 → USDC direct → LawPay)
        payment = await resolve_payment(
            request=request,
            payment_token=req.payment_token,
            usdc_tx_hash=req.usdc_tx_hash,
            price_cents=price_cents,
            service_name=f"IP Consultation - {req.topic}",
            endpoint="/api/v1/consultation/book"
        )

        if not payment["success"]:
            if payment["error"] == "x402_payment_required":
                return JSONResponse(
                    status_code=402,
                    content={"error": "payment_required", "message": "Payment required.",
                             "price": cents_to_usdc_display(price_cents), "payment_methods": "/api/v1/payment-methods"},
                    headers=payment["response_headers"]
                )
            raise HTTPException(status_code=402, detail={
                "error": "payment_failed", "message": payment["error"],
                "payment_methods": "/api/v1/payment-methods"
            })

        consultation_id = f"CON-{uuid.uuid4().hex[:8].upper()}"
        # All consultations currently handled by Brannon McKay
        attorney = "brannon"

        conn.execute("""
            INSERT INTO submissions (order_id, submission_type, status, api_key_id,
                                    org_name, request_data, pricing,
                                    payment_token, payment_verified, payment_verified_at,
                                    ip_address, user_agent, created_at, updated_at, purge_after)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (consultation_id, "consultation", "open", auth["key_id"],
              auth["org"], json.dumps(req.model_dump()),
              json.dumps({"flat_cents": price_cents}),
              payment["transaction_id"], 1, datetime.now(timezone.utc).isoformat(),
              auth["ip"], request.headers.get("user-agent", ""),
              datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(),
              calculate_purge_date(conn)))

        # Insert the opening message from the agent into the thread
        opening_message = f"Topic: {req.topic}"
        if req.description:
            opening_message += f"\n\n{req.description}"

        conn.execute("""
            INSERT INTO consultation_messages (consultation_id, sender_type, sender_name, message, created_at)
            VALUES (?, 'agent', ?, ?, ?)
        """, (consultation_id, req.contact_name, opening_message, datetime.now(timezone.utc).isoformat()))

        conn.commit()

        log_audit_event(conn, "CONSULTATION_OPENED", "api_key", str(auth["key_id"]),
                       ip_address=auth["ip"], endpoint="/api/v1/consultation/book",
                       method="POST", response_status=201,
                       request_summary=f"Consultation: {req.topic}, Attorney: {attorney}")

        response_data = {
            "consultation_id": consultation_id,
            "status": "open",
            "topic": req.topic,
            "attorney": attorney.title(),
            "attorney_email": ATTORNEY_EMAILS.get(attorney, "info@cmblaw.com"),
            "pricing": {"total": "$1.00"},
            "payment": {"verified": True, "transaction_id": payment["transaction_id"], "method": payment["method"]},
            "thread": {
                "message_count": 1,
                "post_url": f"/api/v1/consultation/{consultation_id}/messages",
                "poll_url": f"/api/v1/consultation/{consultation_id}/messages"
            },
            "next_steps": f"Thread opened. Post follow-up messages to /api/v1/consultation/{consultation_id}/messages. "
                          f"Attorney {attorney.title()} will respond asynchronously (typically within 4 business hours). "
                          f"Poll GET /api/v1/consultation/{consultation_id}/messages to check for replies."
        }

        response = JSONResponse(content=response_data, status_code=201)

        # Add x402 payment response header
        for hdr, val in payment["response_headers"].items():
            response.headers[hdr] = val

        # Fire notifications
        try:
            notify_attorneys_new_submission(
                submission_type="consultation",
                order_id=consultation_id,
                org_name=auth["org"],
                request_summary=f"Topic: {req.topic}",
                pricing={"Total": "$1.00"},
                preferred_attorney=attorney
            )
            send_client_confirmation(
                to_email=req.contact_email,
                submission_type="consultation",
                order_id=consultation_id,
                pricing={"Total": "$1.00"},
                next_steps=f"Thread opened. Attorney {attorney.title()} will respond asynchronously (typically within 4 business hours)."
            )
        except Exception as e:
            print(f"Notification error (consultation): {e}")

        return add_rate_limit_headers(response, auth["limits"])
    finally:
        conn.close()


# --- 7b. Consultation — Post Message ---
@app.post("/api/v1/consultation/{consultation_id}/messages")
async def post_consultation_message(
    consultation_id: str,
    req: ConsultationMessageRequest,
    request: Request,
    auth: dict = Depends(validate_api_key)
):
    """Send a message in an existing consultation thread."""
    conn = get_db()
    try:
        consultation_id = sanitize_text(consultation_id, 50)

        # Verify this consultation belongs to the caller
        row = conn.execute(
            "SELECT * FROM submissions WHERE order_id=? AND submission_type='consultation' AND api_key_id=?",
            (consultation_id, auth["key_id"])
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail={
                "error": "consultation_not_found",
                "message": "Consultation thread not found or does not belong to this API key."
            })

        if row["status"] == "closed":
            raise HTTPException(status_code=422, detail={
                "error": "consultation_closed",
                "message": "This consultation thread has been closed. Open a new thread if needed."
            })

        now = datetime.now(timezone.utc).isoformat()

        conn.execute("""
            INSERT INTO consultation_messages (consultation_id, sender_type, sender_name, message, attachments, created_at)
            VALUES (?, 'agent', ?, ?, ?, ?)
        """, (consultation_id, auth["org"], req.message,
              json.dumps(req.attachments or []), now))

        # Update the submission timestamp
        conn.execute("UPDATE submissions SET updated_at=? WHERE order_id=?", (now, consultation_id))
        conn.commit()

        # Get message count
        msg_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM consultation_messages WHERE consultation_id=?",
            (consultation_id,)
        ).fetchone()["cnt"]

        log_audit_event(conn, "CONSULTATION_MESSAGE", "api_key", str(auth["key_id"]),
                       ip_address=auth["ip"], endpoint=f"/api/v1/consultation/{consultation_id}/messages",
                       method="POST", response_status=201,
                       details=f"Message posted to {consultation_id}")

        response_data = {
            "consultation_id": consultation_id,
            "message_posted": True,
            "thread_message_count": msg_count,
            "posted_at": now
        }

        response = JSONResponse(content=response_data, status_code=201)

        # Notify attorney about new message in thread
        try:
            request_data = json.loads(row["request_data"]) if row["request_data"] else {}
            # All consultations currently handled by Brannon McKay
            attorney = "brannon"
            notify_attorney_consultation_message(
                consultation_id=consultation_id,
                attorney=attorney,
                sender_name=auth["org"],
                message_preview=req.message,
                thread_message_count=msg_count
            )
        except Exception as e:
            print(f"Notification error (consultation msg): {e}")

        return add_rate_limit_headers(response, auth["limits"])
    finally:
        conn.close()


# --- 7c. Consultation — Get Messages ---
@app.get("/api/v1/consultation/{consultation_id}/messages")
async def get_consultation_messages(
    consultation_id: str,
    request: Request,
    since: str = None,
    auth: dict = Depends(validate_api_key)
):
    """Retrieve messages in a consultation thread. Use ?since=ISO_TIMESTAMP to get only new messages."""
    conn = get_db()
    try:
        consultation_id = sanitize_text(consultation_id, 50)

        # Verify ownership
        row = conn.execute(
            "SELECT * FROM submissions WHERE order_id=? AND submission_type='consultation' AND api_key_id=?",
            (consultation_id, auth["key_id"])
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail={
                "error": "consultation_not_found",
                "message": "Consultation thread not found or does not belong to this API key."
            })

        # Fetch messages
        if since:
            since = sanitize_text(since, 50)
            messages_rows = conn.execute(
                "SELECT * FROM consultation_messages WHERE consultation_id=? AND created_at > ? ORDER BY created_at ASC",
                (consultation_id, since)
            ).fetchall()
        else:
            messages_rows = conn.execute(
                "SELECT * FROM consultation_messages WHERE consultation_id=? ORDER BY created_at ASC",
                (consultation_id,)
            ).fetchall()

        messages = []
        for msg in messages_rows:
            messages.append({
                "id": msg["id"],
                "sender_type": msg["sender_type"],
                "sender_name": msg["sender_name"],
                "message": msg["message"],
                "attachments": json.loads(msg["attachments"]) if msg["attachments"] else [],
                "created_at": msg["created_at"],
                "read_at": msg["read_at"]
            })

        # Mark attorney messages as read
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE consultation_messages SET read_at=? WHERE consultation_id=? AND sender_type='attorney' AND read_at IS NULL",
            (now, consultation_id)
        )
        conn.commit()

        # Count unread attorney messages (before we marked them)
        has_new_attorney_reply = any(
            m["sender_type"] == "attorney" and m["read_at"] is None
            for m in messages_rows
        )

        log_audit_event(conn, "CONSULTATION_POLL", "api_key", str(auth["key_id"]),
                       ip_address=auth["ip"], endpoint=f"/api/v1/consultation/{consultation_id}/messages",
                       method="GET", response_status=200,
                       details=f"Retrieved {len(messages)} messages")

        response_data = {
            "consultation_id": consultation_id,
            "status": row["status"],
            "total_messages": len(messages),
            "has_new_attorney_reply": has_new_attorney_reply,
            "messages": messages,
            "retrieved_at": now
        }

        response = JSONResponse(content=response_data)
        return add_rate_limit_headers(response, auth["limits"])
    finally:
        conn.close()


# --- Admin Endpoints ---

@app.post("/api/admin/kill-switch")
async def toggle_kill_switch(request: Request, admin: dict = Depends(validate_admin_key)):
    conn = get_db()
    try:
        body = await request.json()
        enabled = body.get("enabled", True)
        set_setting(conn, "intake_enabled", "true" if enabled else "false")

        log_audit_event(conn, "KILL_SWITCH_TOGGLED", "admin", str(admin["admin_id"]),
                       ip_address=admin["ip"], endpoint="/api/admin/kill-switch",
                       method="POST", details=f"Intake {'enabled' if enabled else 'PAUSED'} by {admin['name']}")

        return {"intake_enabled": enabled, "message": f"Intake {'enabled' if enabled else 'PAUSED'}"}
    finally:
        conn.close()


@app.post("/api/admin/keys/create")
async def create_api_key_endpoint(request: Request, admin: dict = Depends(validate_admin_key)):
    conn = get_db()
    try:
        body = await request.json()
        org_name = sanitize_text(body.get("org_name", ""), 200)
        org_email = body.get("org_email", "")
        allowed_ips = body.get("allowed_ips")

        if not org_name or not org_email:
            raise HTTPException(status_code=422, detail={"error": "org_name and org_email required"})

        key, key_hash = generate_api_key()
        now = datetime.now(timezone.utc).isoformat()

        conn.execute("""
            INSERT INTO api_keys (key_hash, key_prefix, org_name, org_email, scopes, active,
                                 allowed_ips, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """, (key_hash, key[:16], org_name, org_email, '["read","write"]',
              json.dumps(allowed_ips) if allowed_ips else None, now))
        conn.commit()

        log_audit_event(conn, "API_KEY_CREATED", "admin", str(admin["admin_id"]),
                       ip_address=admin["ip"], endpoint="/api/admin/keys/create",
                       method="POST", details=f"Key created for {org_name} ({org_email})")

        return {
            "api_key": key,
            "org_name": org_name,
            "message": "Store this key securely — it cannot be retrieved again."
        }
    finally:
        conn.close()


@app.post("/api/admin/keys/revoke")
async def revoke_api_key_endpoint(request: Request, admin: dict = Depends(validate_admin_key)):
    conn = get_db()
    try:
        body = await request.json()
        key_prefix = body.get("key_prefix", "")
        reason = sanitize_text(body.get("reason", "Revoked by admin"), 500)

        row = conn.execute("SELECT id, org_name FROM api_keys WHERE key_prefix=?", (key_prefix,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Key not found"})

        conn.execute("UPDATE api_keys SET active=0, revoked_at=?, revoke_reason=? WHERE id=?",
                     (datetime.now(timezone.utc).isoformat(), reason, row["id"]))
        conn.commit()

        log_audit_event(conn, "API_KEY_REVOKED", "admin", str(admin["admin_id"]),
                       ip_address=admin["ip"], details=f"Revoked key for {row['org_name']}: {reason}")

        return {"message": f"Key for {row['org_name']} revoked", "reason": reason}
    finally:
        conn.close()


@app.post("/api/admin/unpause-key")
async def unpause_key(request: Request, admin: dict = Depends(validate_admin_key)):
    conn = get_db()
    try:
        body = await request.json()
        key_prefix = body.get("key_prefix", "")

        row = conn.execute("SELECT id, org_name FROM api_keys WHERE key_prefix=?", (key_prefix,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Key not found"})

        conn.execute("UPDATE api_keys SET paused_for_abuse=0 WHERE id=?", (row["id"],))
        conn.commit()

        log_audit_event(conn, "API_KEY_UNPAUSED", "admin", str(admin["admin_id"]),
                       ip_address=admin["ip"], details=f"Unpaused key for {row['org_name']}")

        return {"message": f"Key for {row['org_name']} unpaused"}
    finally:
        conn.close()


@app.get("/api/admin/submissions")
async def list_submissions(admin: dict = Depends(validate_admin_key)):
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM submissions ORDER BY created_at DESC LIMIT 100").fetchall()
        submissions = []
        for row in rows:
            submissions.append({
                "order_id": row["order_id"],
                "matter_id": row["matter_id"],
                "type": row["submission_type"],
                "status": row["status"],
                "org": row["org_name"],
                "payment_verified": bool(row["payment_verified"]),
                "created_at": row["created_at"],
                "ip_address": row["ip_address"]
            })

        return {"total": len(submissions), "submissions": submissions,
                "intake_enabled": get_setting(conn, "intake_enabled") == "true"}
    finally:
        conn.close()


@app.get("/api/admin/audit-log")
async def get_audit_log(limit: int = 50, admin: dict = Depends(validate_admin_key)):
    conn = get_db()
    try:
        limit = min(limit, 500)
        rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        entries = []
        for row in rows:
            entries.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "event_type": row["event_type"],
                "actor_type": row["actor_type"],
                "actor_id": row["actor_id"],
                "ip_address": row["ip_address"],
                "endpoint": row["endpoint"],
                "response_status": row["response_status"],
                "details": row["details"],
                "entry_hash": row["entry_hash"]
            })
        return {"total": len(entries), "entries": entries}
    finally:
        conn.close()


@app.post("/api/admin/purge-expired")
async def purge_expired(admin: dict = Depends(validate_admin_key)):
    conn = get_db()
    try:
        purged = purge_expired_data(conn)
        return {"purged_submissions": purged}
    finally:
        conn.close()


@app.post("/api/admin/consultation/{consultation_id}/reply")
async def attorney_reply(consultation_id: str, request: Request, admin: dict = Depends(validate_admin_key)):
    """Attorney posts a reply in a consultation thread. Fires webhook if configured."""
    conn = get_db()
    try:
        body = await request.json()
        message = sanitize_text(body.get("message", ""), 10000)
        if not message:
            raise HTTPException(status_code=422, detail={"error": "Message is required"})

        consultation_id = sanitize_text(consultation_id, 50)

        # Find the consultation
        row = conn.execute(
            "SELECT * FROM submissions WHERE order_id=? AND submission_type='consultation'",
            (consultation_id,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail={"error": "Consultation not found"})

        if row["status"] == "closed":
            raise HTTPException(status_code=422, detail={"error": "Consultation is closed"})

        now = datetime.now(timezone.utc).isoformat()

        conn.execute("""
            INSERT INTO consultation_messages (consultation_id, sender_type, sender_name, message, created_at)
            VALUES (?, 'attorney', ?, ?, ?)
        """, (consultation_id, admin["name"], message, now))

        conn.execute("UPDATE submissions SET updated_at=? WHERE order_id=?", (now, consultation_id))
        conn.commit()

        msg_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]

        log_audit_event(conn, "ATTORNEY_REPLY", "admin", str(admin["admin_id"]),
                       ip_address=admin["ip"],
                       endpoint=f"/api/admin/consultation/{consultation_id}/reply",
                       method="POST", response_status=201,
                       details=f"Attorney {admin['name']} replied in {consultation_id}")

        # Fire webhook if configured
        webhook_url = conn.execute(
            "SELECT webhook_url FROM api_keys WHERE id=?", (row["api_key_id"],)
        ).fetchone()

        webhook_sent = False
        if webhook_url and webhook_url["webhook_url"]:
            try:
                webhook_sent = await fire_consultation_reply_webhook(
                    consultation_id=consultation_id,
                    webhook_url=webhook_url["webhook_url"],
                    attorney_name=admin["name"],
                    message=message,
                    message_id=msg_id
                )
            except Exception as e:
                print(f"Webhook error: {e}")

        return {
            "consultation_id": consultation_id,
            "message_posted": True,
            "message_id": msg_id,
            "webhook_sent": webhook_sent,
            "posted_at": now
        }
    finally:
        conn.close()


@app.put("/api/admin/keys/webhook")
async def set_webhook_url(request: Request, admin: dict = Depends(validate_admin_key)):
    """Set or update the webhook URL for an API key."""
    conn = get_db()
    try:
        body = await request.json()
        key_prefix = body.get("key_prefix", "")
        webhook_url = body.get("webhook_url", "")

        row = conn.execute("SELECT id, org_name FROM api_keys WHERE key_prefix=?", (key_prefix,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Key not found"})

        # Validate URL if provided
        if webhook_url:
            from validation import sanitize_url
            valid, result = sanitize_url(webhook_url)
            if not valid:
                raise HTTPException(status_code=422, detail={"error": f"Invalid webhook URL: {result}"})
            webhook_url = result

        conn.execute("UPDATE api_keys SET webhook_url=? WHERE id=?", (webhook_url or None, row["id"]))
        conn.commit()

        log_audit_event(conn, "WEBHOOK_CONFIGURED", "admin", str(admin["admin_id"]),
                       ip_address=admin["ip"],
                       details=f"Webhook {'set' if webhook_url else 'cleared'} for {row['org_name']}")

        return {"message": f"Webhook {'set' if webhook_url else 'cleared'} for {row['org_name']}", "webhook_url": webhook_url}
    finally:
        conn.close()


# --- OpenAPI Schema ---
@app.get("/api/v1/openapi.json")
async def get_openapi_schema():
    return app.openapi()


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)

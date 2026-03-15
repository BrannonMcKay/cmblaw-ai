#!/usr/bin/env python3
"""
notifications.py — Email notification system for cmblaw.ai

Handles:
- Attorney email notifications on new submissions
- Attorney notifications on new consultation messages
- Client email confirmations on submission
- Webhook callbacks for consultation replies

Configuration:
  Set environment variables:
    SMTP_HOST      — SMTP server hostname (e.g., smtp.gmail.com)
    SMTP_PORT      — SMTP port (default: 587)
    SMTP_USER      — SMTP username / sender email
    SMTP_PASSWORD  — SMTP password or app password
    SMTP_FROM      — From address (default: noreply@cmblaw.ai)
    SMTP_ENABLED   — Set to "true" to enable email sending (default: false, logs only)
"""

import os
import json
import smtplib
import ssl
import hashlib
import hmac
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger("cmblaw.notifications")

# --- SMTP Configuration ---
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@cmblaw.ai")
SMTP_ENABLED = os.environ.get("SMTP_ENABLED", "false").lower() == "true"

# HMAC secret for webhook signatures
WEBHOOK_SECRET = os.environ.get("CMBLAW_WEBHOOK_SECRET", os.environ.get("CMBLAW_HMAC_SECRET", "cmblaw-ai-dev-secret-key-2026"))

# Attorney routing
ATTORNEY_EMAILS = {
    "brannon": "brannon@cmblaw.com",
    "josh": "josh@cmblaw.com",
    "ben": "ben@cmblaw.com",
    "ginger": "ginger@cmblaw.com",
    "manoj": "manoj@cmblaw.com",
    "becky": "becky@cmblaw.com",
    "info": "info@cmblaw.com"
}

# Service type → attorney routing (default assignment)
SERVICE_ATTORNEY_MAP = {
    "trademark_filing": ["brannon", "becky"],
    "provisional_patent": ["brannon", "ginger"],
    "entity_formation": ["josh", "becky"],
    "trademark_monitoring": ["brannon", "becky"],  # Deprecated — toolkit replaced endpoint
    "document_generation": ["brannon", "becky"],
    "consultation": ["brannon"]  # All consultations handled by Brannon McKay initially
}


def _send_email(to: str, subject: str, html_body: str, text_body: str = None):
    """Send an email via SMTP. Falls back to logging if SMTP is not configured."""
    if not SMTP_ENABLED or not SMTP_USER or not SMTP_PASSWORD:
        logger.info(f"[EMAIL-LOG] To: {to} | Subject: {subject}")
        logger.debug(f"[EMAIL-LOG] Body: {text_body or html_body[:200]}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"cmblaw.ai <{SMTP_FROM}>"
        msg["To"] = to
        msg["Reply-To"] = "info@cmblaw.com"

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to, msg.as_string())

        logger.info(f"[EMAIL-SENT] To: {to} | Subject: {subject}")
        return True

    except Exception as e:
        logger.error(f"[EMAIL-FAILED] To: {to} | Subject: {subject} | Error: {e}")
        return False


def _email_wrapper(content_html: str, title: str) -> str:
    """Wrap content in a branded email template."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0; padding:0; background:#f4f4f5; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<div style="max-width:600px; margin:0 auto; padding:24px;">
  <div style="background:#0a1628; padding:20px 24px; border-radius:8px 8px 0 0;">
    <h1 style="color:#fff; font-size:18px; margin:0; font-weight:600;">cmblaw.ai</h1>
    <p style="color:#8b99b0; font-size:12px; margin:4px 0 0;">Clayton, McKay &amp; Bailey, PC</p>
  </div>
  <div style="background:#fff; padding:24px; border:1px solid #e4e4e7; border-top:none;">
    <h2 style="color:#0a1628; font-size:16px; margin:0 0 16px; font-weight:600;">{title}</h2>
    {content_html}
  </div>
  <div style="padding:16px 24px; text-align:center;">
    <p style="color:#71717a; font-size:11px; margin:0;">
      Clayton, McKay &amp; Bailey, PC &bull; 800 Battery Ave. SE, Suite 300, Atlanta, GA 30339<br>
      (404) 414-8633 &bull; info@cmblaw.com
    </p>
  </div>
</div>
</body>
</html>"""


# --- Attorney Notifications ---

def notify_attorneys_new_submission(
    submission_type: str,
    order_id: str,
    org_name: str,
    request_summary: str,
    pricing: dict,
    preferred_attorney: str = None
):
    """Send email notification to assigned attorney(s) about a new submission."""
    type_labels = {
        "trademark_filing": "Trademark Filing",
        "provisional_patent": "U.S. Provisional Patent Application",
        "entity_formation": "Business Entity Formation",
        "trademark_monitoring": "Trademark Monitoring",
        "document_generation": "Document Generation",
        "consultation": "IP Consultation"
    }

    label = type_labels.get(submission_type, submission_type)

    # Determine recipients
    recipients = []
    if preferred_attorney and preferred_attorney in ATTORNEY_EMAILS:
        recipients.append(ATTORNEY_EMAILS[preferred_attorney])
    else:
        attorney_keys = SERVICE_ATTORNEY_MAP.get(submission_type, ["brannon"])
        recipients = [ATTORNEY_EMAILS[k] for k in attorney_keys if k in ATTORNEY_EMAILS]

    # Always CC info@
    if "info@cmblaw.com" not in recipients:
        recipients.append("info@cmblaw.com")

    pricing_html = ""
    if pricing:
        pricing_lines = []
        for k, v in pricing.items():
            pricing_lines.append(f"<li style='color:#374151; font-size:14px;'><strong>{k}:</strong> {v}</li>")
        pricing_html = f"<ul style='margin:8px 0; padding-left:20px;'>{''.join(pricing_lines)}</ul>"

    content = f"""
    <p style="color:#374151; font-size:14px; line-height:1.6; margin:0 0 12px;">
      A new <strong>{label}</strong> submission has been received via the cmblaw.ai API.
    </p>
    <table style="width:100%; border-collapse:collapse; margin:16px 0;">
      <tr><td style="padding:8px 12px; background:#f9fafb; border:1px solid #e5e7eb; font-size:13px; color:#6b7280; width:140px;">Order ID</td>
          <td style="padding:8px 12px; border:1px solid #e5e7eb; font-size:13px; color:#111827; font-family:monospace;">{order_id}</td></tr>
      <tr><td style="padding:8px 12px; background:#f9fafb; border:1px solid #e5e7eb; font-size:13px; color:#6b7280;">Service</td>
          <td style="padding:8px 12px; border:1px solid #e5e7eb; font-size:13px; color:#111827;">{label}</td></tr>
      <tr><td style="padding:8px 12px; background:#f9fafb; border:1px solid #e5e7eb; font-size:13px; color:#6b7280;">Client</td>
          <td style="padding:8px 12px; border:1px solid #e5e7eb; font-size:13px; color:#111827;">{org_name}</td></tr>
      <tr><td style="padding:8px 12px; background:#f9fafb; border:1px solid #e5e7eb; font-size:13px; color:#6b7280;">Summary</td>
          <td style="padding:8px 12px; border:1px solid #e5e7eb; font-size:13px; color:#111827;">{request_summary}</td></tr>
    </table>
    {pricing_html}
    <p style="color:#6b7280; font-size:13px; line-height:1.5; margin:16px 0 0;">
      Payment has been verified. Please review and process this submission at your earliest convenience.
    </p>
    """

    subject = f"[cmblaw.ai] New {label}: {order_id}"
    html = _email_wrapper(content, f"New {label} Received")

    for recipient in recipients:
        _send_email(recipient, subject, html,
                   text_body=f"New {label} received.\nOrder: {order_id}\nClient: {org_name}\nSummary: {request_summary}")


def notify_attorney_consultation_message(
    consultation_id: str,
    attorney: str,
    sender_name: str,
    message_preview: str,
    thread_message_count: int
):
    """Notify an attorney about a new message in a consultation thread."""
    recipient = ATTORNEY_EMAILS.get(attorney, "info@cmblaw.com")

    content = f"""
    <p style="color:#374151; font-size:14px; line-height:1.6; margin:0 0 12px;">
      A new message has been posted in consultation thread <strong style="font-family:monospace;">{consultation_id}</strong>.
    </p>
    <div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:6px; padding:16px; margin:16px 0;">
      <p style="color:#6b7280; font-size:12px; margin:0 0 8px;">From: <strong style="color:#111827;">{sender_name}</strong></p>
      <p style="color:#374151; font-size:14px; line-height:1.5; margin:0; white-space:pre-wrap;">{message_preview[:500]}</p>
    </div>
    <p style="color:#6b7280; font-size:13px; margin:12px 0 0;">
      Thread contains {thread_message_count} message(s). Please respond when available.
    </p>
    """

    subject = f"[cmblaw.ai] New message in {consultation_id}"
    html = _email_wrapper(content, "New Consultation Message")
    _send_email(recipient, subject, html,
               text_body=f"New message in {consultation_id} from {sender_name}: {message_preview[:200]}")


# --- Client Confirmations ---

def send_client_confirmation(
    to_email: str,
    submission_type: str,
    order_id: str,
    matter_id: str = None,
    pricing: dict = None,
    timeline: str = None,
    next_steps: str = None
):
    """Send confirmation email to the client/agent contact email."""
    type_labels = {
        "trademark_filing": "Trademark Filing",
        "provisional_patent": "U.S. Provisional Patent Application",
        "entity_formation": "Business Entity Formation",
        "trademark_monitoring": "Trademark Monitoring",
        "document_generation": "Document Generation",
        "consultation": "IP Consultation"
    }

    label = type_labels.get(submission_type, submission_type)

    pricing_html = ""
    if pricing:
        pricing_lines = []
        for k, v in pricing.items():
            if not k.startswith("_"):
                pricing_lines.append(f"<tr><td style='padding:6px 12px; border:1px solid #e5e7eb; font-size:13px; color:#6b7280;'>{k}</td><td style='padding:6px 12px; border:1px solid #e5e7eb; font-size:13px; color:#111827;'>{v}</td></tr>")
        if pricing_lines:
            pricing_html = f"<table style='width:100%; border-collapse:collapse; margin:12px 0;'>{''.join(pricing_lines)}</table>"

    ids_html = f"<li style='color:#374151; font-size:14px;'>Order ID: <code style='background:#f4f4f5; padding:2px 6px; border-radius:3px; font-size:13px;'>{order_id}</code></li>"
    if matter_id:
        ids_html += f"<li style='color:#374151; font-size:14px;'>Matter ID: <code style='background:#f4f4f5; padding:2px 6px; border-radius:3px; font-size:13px;'>{matter_id}</code></li>"

    content = f"""
    <p style="color:#374151; font-size:14px; line-height:1.6; margin:0 0 12px;">
      Your <strong>{label}</strong> submission has been received and payment verified.
    </p>
    <ul style="margin:12px 0; padding-left:20px;">
      {ids_html}
    </ul>
    {pricing_html}
    {"<p style='color:#374151; font-size:14px; margin:12px 0;'><strong>Estimated Timeline:</strong> " + timeline + "</p>" if timeline else ""}
    {"<p style='color:#374151; font-size:14px; line-height:1.6; margin:12px 0;'><strong>Next Steps:</strong> " + next_steps + "</p>" if next_steps else ""}
    <p style="color:#6b7280; font-size:13px; line-height:1.5; margin:16px 0 0;">
      You can check the status of your submission at any time using the
      <code style="background:#f4f4f5; padding:2px 6px; border-radius:3px; font-size:12px;">GET /api/v1/portfolio/status</code> endpoint.
    </p>
    """

    subject = f"[cmblaw.ai] {label} Confirmed — {order_id}"
    html = _email_wrapper(content, f"{label} Confirmation")
    _send_email(to_email, subject, html,
               text_body=f"Your {label} has been received.\nOrder: {order_id}\n{f'Matter: {matter_id}' if matter_id else ''}\n{f'Timeline: {timeline}' if timeline else ''}\n{f'Next: {next_steps}' if next_steps else ''}")


# --- Webhook Callbacks ---

def compute_webhook_signature(payload: str) -> str:
    """Compute HMAC-SHA256 signature for webhook payload."""
    return hmac.new(WEBHOOK_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


async def send_webhook_callback(
    webhook_url: str,
    event_type: str,
    consultation_id: str,
    data: dict
):
    """Send a webhook callback to the registered URL with HMAC signature."""
    import aiohttp

    payload = json.dumps({
        "event": event_type,
        "consultation_id": consultation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data
    }, sort_keys=True)

    signature = compute_webhook_signature(payload)

    headers = {
        "Content-Type": "application/json",
        "X-CMBLaw-Signature": f"sha256={signature}",
        "X-CMBLaw-Event": event_type,
        "User-Agent": "cmblaw.ai-webhook/1.0"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                data=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                success = resp.status < 400
                logger.info(f"[WEBHOOK] {event_type} -> {webhook_url} | Status: {resp.status}")
                return success
    except Exception as e:
        logger.error(f"[WEBHOOK-FAILED] {event_type} -> {webhook_url} | Error: {e}")
        return False


async def fire_consultation_reply_webhook(
    consultation_id: str,
    webhook_url: str,
    attorney_name: str,
    message: str,
    message_id: int
):
    """Fire a webhook when an attorney replies in a consultation thread."""
    if not webhook_url:
        return False

    return await send_webhook_callback(
        webhook_url=webhook_url,
        event_type="consultation.reply",
        consultation_id=consultation_id,
        data={
            "message_id": message_id,
            "sender_type": "attorney",
            "sender_name": attorney_name,
            "message_preview": message[:500],
            "full_message_available": len(message) > 500,
            "poll_url": f"/api/v1/consultation/{consultation_id}/messages"
        }
    )


async def fire_status_update_webhook(
    webhook_url: str,
    order_id: str,
    new_status: str,
    details: str = None
):
    """Fire a webhook when a submission status changes."""
    if not webhook_url:
        return False

    return await send_webhook_callback(
        webhook_url=webhook_url,
        event_type="submission.status_updated",
        consultation_id=order_id,
        data={
            "order_id": order_id,
            "new_status": new_status,
            "details": details,
            "portfolio_url": "/api/v1/portfolio/status"
        }
    )

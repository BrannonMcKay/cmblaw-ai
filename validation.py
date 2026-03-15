#!/usr/bin/env python3
"""
validation.py — Input validation and sanitization for cmblaw.ai

Strict validation on all inputs: length limits, format checks, URL validation,
content sanitization, and field-specific rules.
"""

import re
import html
from urllib.parse import urlparse
from pydantic import BaseModel, field_validator, EmailStr, Field
from typing import Optional


# --- Constants ---

MAX_NAME_LENGTH = 200
MAX_ADDRESS_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 5000
MAX_SHORT_TEXT = 500
MAX_URL_LENGTH = 2048
MAX_EMAIL_LENGTH = 254
MAX_PHONE_LENGTH = 20
MAX_CLASSES = 45  # USPTO has 45 classes
MAX_PARTIES = 10
MAX_TIMES = 10
MAX_URLS = 20
MAX_SCOPE_ITEMS = 5

VALID_ENTITY_TYPES = ["individual", "corporation", "llc", "partnership", "trust", "nonprofit", "sole_proprietorship"]
VALID_FORMATION_TYPES = ["LLC", "Corp", "S-Corp", "C-Corp", "LP", "LLP", "PLLC", "PC", "Nonprofit"]
VALID_FILING_BASIS = ["use", "intent", "foreign_registration", "foreign_application"]
VALID_DOCUMENT_TYPES = ["NDA", "IP_assignment", "CIIA", "consulting_agreement", "license_agreement", "agent_authorization", "agent_service_agreement"]
VALID_MONITOR_SCOPES = ["uspto", "common_law", "domains", "international"]
VALID_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
]

# Blocked URL schemes
BLOCKED_SCHEMES = ["javascript", "data", "vbscript", "file", "ftp"]


# --- Sanitization Helpers ---

def sanitize_text(text: str, max_length: int = MAX_SHORT_TEXT) -> str:
    """Sanitize text input: strip, limit length, escape HTML entities."""
    if not text:
        return text
    text = text.strip()
    text = html.escape(text, quote=True)
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text[:max_length]


def sanitize_url(url: str) -> tuple[bool, str]:
    """Validate and sanitize a URL. Returns (is_valid, sanitized_url_or_error)."""
    if not url:
        return True, ""

    url = url.strip()
    if len(url) > MAX_URL_LENGTH:
        return False, f"URL exceeds maximum length of {MAX_URL_LENGTH} characters"

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    # Check scheme
    if not parsed.scheme:
        return False, "URL must include a scheme (https://)"

    if parsed.scheme.lower() in BLOCKED_SCHEMES:
        return False, f"URL scheme '{parsed.scheme}' is not allowed"

    if parsed.scheme.lower() not in ["http", "https"]:
        return False, "Only http:// and https:// URLs are accepted"

    # Prefer HTTPS
    if parsed.scheme.lower() == "http":
        url = "https" + url[4:]

    # Check for private/internal IPs
    hostname = parsed.hostname
    if hostname:
        hostname_lower = hostname.lower()
        blocked_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.", "10.", "192.168.", "172.16."]
        for blocked in blocked_hosts:
            if hostname_lower.startswith(blocked) or hostname_lower == blocked:
                return False, "Internal/private URLs are not allowed"

    if not parsed.netloc:
        return False, "URL must include a domain"

    return True, url


def validate_email(email: str) -> tuple[bool, str]:
    """Basic email validation."""
    if not email:
        return False, "Email is required"

    email = email.strip().lower()
    if len(email) > MAX_EMAIL_LENGTH:
        return False, f"Email exceeds maximum length of {MAX_EMAIL_LENGTH} characters"

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"

    return True, email


def validate_phone(phone: str) -> tuple[bool, str]:
    """Basic phone validation."""
    if not phone:
        return True, ""

    phone = re.sub(r'[^\d+\-\(\)\s]', '', phone.strip())
    if len(phone) > MAX_PHONE_LENGTH:
        return False, "Phone number too long"

    digits = re.sub(r'[^\d]', '', phone)
    if len(digits) < 7 or len(digits) > 15:
        return False, "Phone number must have 7-15 digits"

    return True, phone


def validate_payment_token(token: str) -> tuple[bool, str]:
    """Validate payment token format."""
    if not token:
        return False, "Payment token is required"

    token = token.strip()
    if len(token) > 500:
        return False, "Invalid payment token"

    # Basic format check — in production, this validates against LawPay
    if len(token) < 5:
        return False, "Invalid payment token format"

    return True, token


# --- Pydantic Models with Validation ---

class TrademarkFilingRequest(BaseModel):
    applicant_name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    applicant_address: str = Field(default="", max_length=MAX_ADDRESS_LENGTH)
    entity_type: str = Field(default="individual", max_length=50)
    mark_text: str = Field(..., min_length=1, max_length=MAX_SHORT_TEXT)
    mark_image_url: Optional[str] = Field(default=None, max_length=MAX_URL_LENGTH)
    goods_services_description: str = Field(..., min_length=10, max_length=MAX_DESCRIPTION_LENGTH)
    uspto_classes: list[int] = Field(..., min_length=1, max_length=MAX_CLASSES)
    specimen_url: Optional[str] = Field(default=None, max_length=MAX_URL_LENGTH)
    filing_basis: str = Field(default="intent", max_length=50)
    contact_email: str = Field(..., max_length=MAX_EMAIL_LENGTH)
    payment_token: Optional[str] = Field(default=None, max_length=500)
    usdc_tx_hash: Optional[str] = Field(default=None, max_length=66)

    @field_validator('entity_type')
    @classmethod
    def validate_entity_type(cls, v):
        v = v.strip().lower()
        if v not in VALID_ENTITY_TYPES:
            raise ValueError(f"Invalid entity type. Must be one of: {', '.join(VALID_ENTITY_TYPES)}")
        return v

    @field_validator('filing_basis')
    @classmethod
    def validate_filing_basis(cls, v):
        v = v.strip().lower()
        if v not in VALID_FILING_BASIS:
            raise ValueError(f"Invalid filing basis. Must be one of: {', '.join(VALID_FILING_BASIS)}")
        return v

    @field_validator('uspto_classes')
    @classmethod
    def validate_classes(cls, v):
        for c in v:
            if c < 1 or c > 45:
                raise ValueError(f"USPTO class must be between 1 and 45, got {c}")
        if len(set(v)) != len(v):
            raise ValueError("Duplicate USPTO classes are not allowed")
        return v

    @field_validator('mark_image_url', 'specimen_url')
    @classmethod
    def validate_urls(cls, v):
        if v is None:
            return v
        valid, result = sanitize_url(v)
        if not valid:
            raise ValueError(result)
        return result

    @field_validator('contact_email')
    @classmethod
    def validate_contact_email(cls, v):
        valid, result = validate_email(v)
        if not valid:
            raise ValueError(result)
        return result

    @field_validator('applicant_name', 'mark_text', 'goods_services_description', 'applicant_address')
    @classmethod
    def sanitize_text_fields(cls, v):
        return sanitize_text(v, MAX_DESCRIPTION_LENGTH)


class ProvisionalPatentRequest(BaseModel):
    problem_statement: str = Field(..., min_length=20, max_length=MAX_DESCRIPTION_LENGTH)
    solution_description: str = Field(..., min_length=20, max_length=MAX_DESCRIPTION_LENGTH)
    differentiation: str = Field(..., min_length=20, max_length=MAX_DESCRIPTION_LENGTH)
    system_diagram_url: str = Field(..., min_length=1, max_length=MAX_URL_LENGTH)
    flowcharts: Optional[list[str]] = Field(default=None, max_length=MAX_URLS)
    sequence_diagrams: Optional[list[str]] = Field(default=None, max_length=MAX_URLS)
    contact_email: str = Field(..., max_length=MAX_EMAIL_LENGTH)
    payment_token: Optional[str] = Field(default=None, max_length=500)
    usdc_tx_hash: Optional[str] = Field(default=None, max_length=66)

    @field_validator('system_diagram_url')
    @classmethod
    def validate_diagram_url(cls, v):
        valid, result = sanitize_url(v)
        if not valid:
            raise ValueError(result)
        return result

    @field_validator('flowcharts', 'sequence_diagrams')
    @classmethod
    def validate_url_lists(cls, v):
        if v is None:
            return v
        validated = []
        for url in v:
            valid, result = sanitize_url(url)
            if not valid:
                raise ValueError(f"Invalid URL in list: {result}")
            validated.append(result)
        return validated

    @field_validator('contact_email')
    @classmethod
    def validate_contact_email(cls, v):
        valid, result = validate_email(v)
        if not valid:
            raise ValueError(result)
        return result

    @field_validator('problem_statement', 'solution_description', 'differentiation')
    @classmethod
    def sanitize_text_fields(cls, v):
        return sanitize_text(v, MAX_DESCRIPTION_LENGTH)


class EntityFormationRequest(BaseModel):
    entity_type: str = Field(default="LLC", max_length=50)
    entity_name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    state: str = Field(default="GA", max_length=2)
    registered_agent: Optional[dict] = None
    members_or_officers: list[dict] = Field(default=[], max_length=20)
    contact_email: str = Field(..., max_length=MAX_EMAIL_LENGTH)
    payment_token: Optional[str] = Field(default=None, max_length=500)
    usdc_tx_hash: Optional[str] = Field(default=None, max_length=66)

    @field_validator('entity_type')
    @classmethod
    def validate_formation_type(cls, v):
        v = v.strip()
        if v not in VALID_FORMATION_TYPES:
            raise ValueError(f"Invalid entity type. Must be one of: {', '.join(VALID_FORMATION_TYPES)}")
        return v

    @field_validator('state')
    @classmethod
    def validate_state(cls, v):
        v = v.strip().upper()
        if v not in VALID_STATES:
            raise ValueError(f"Invalid state code. Must be a valid US state abbreviation.")
        return v

    @field_validator('contact_email')
    @classmethod
    def validate_contact_email(cls, v):
        valid, result = validate_email(v)
        if not valid:
            raise ValueError(result)
        return result

    @field_validator('entity_name')
    @classmethod
    def sanitize_name(cls, v):
        return sanitize_text(v, MAX_NAME_LENGTH)


class TrademarkMonitorRequest(BaseModel):
    mark_text: str = Field(..., min_length=1, max_length=MAX_SHORT_TEXT)
    registration_number: Optional[str] = Field(default=None, max_length=50)
    classes: list[int] = Field(default=[], max_length=MAX_CLASSES)
    alert_email: str = Field(..., max_length=MAX_EMAIL_LENGTH)
    scope: list[str] = Field(default=["uspto", "common_law", "domains"], max_length=MAX_SCOPE_ITEMS)
    payment_token: Optional[str] = Field(default=None, max_length=500)
    usdc_tx_hash: Optional[str] = Field(default=None, max_length=66)

    @field_validator('scope')
    @classmethod
    def validate_scope(cls, v):
        for item in v:
            if item not in VALID_MONITOR_SCOPES:
                raise ValueError(f"Invalid scope: {item}. Must be one of: {', '.join(VALID_MONITOR_SCOPES)}")
        return v

    @field_validator('classes')
    @classmethod
    def validate_classes(cls, v):
        for c in v:
            if c < 1 or c > 45:
                raise ValueError(f"USPTO class must be between 1 and 45")
        return v

    @field_validator('alert_email')
    @classmethod
    def validate_alert_email(cls, v):
        valid, result = validate_email(v)
        if not valid:
            raise ValueError(result)
        return result

    @field_validator('mark_text')
    @classmethod
    def sanitize_mark(cls, v):
        return sanitize_text(v, MAX_SHORT_TEXT)


class DocumentGenerateRequest(BaseModel):
    document_type: str = Field(..., max_length=50)
    parties: list[dict] = Field(..., min_length=1, max_length=MAX_PARTIES)
    terms: dict = Field(default={})
    contact_email: str = Field(..., max_length=MAX_EMAIL_LENGTH)
    payment_token: Optional[str] = Field(default=None, max_length=500)
    usdc_tx_hash: Optional[str] = Field(default=None, max_length=66)

    @field_validator('document_type')
    @classmethod
    def validate_doc_type(cls, v):
        v = v.strip()
        if v not in VALID_DOCUMENT_TYPES:
            raise ValueError(f"Invalid document type. Must be one of: {', '.join(VALID_DOCUMENT_TYPES)}")
        return v

    @field_validator('contact_email')
    @classmethod
    def validate_contact_email(cls, v):
        valid, result = validate_email(v)
        if not valid:
            raise ValueError(result)
        return result


class ConsultationBookRequest(BaseModel):
    """Open an async consultation thread with a CMB attorney."""
    topic: str = Field(..., min_length=5, max_length=MAX_SHORT_TEXT)
    description: str = Field(default="", max_length=MAX_DESCRIPTION_LENGTH)
    contact_name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    contact_email: str = Field(..., max_length=MAX_EMAIL_LENGTH)
    payment_token: Optional[str] = Field(default=None, max_length=500)
    usdc_tx_hash: Optional[str] = Field(default=None, max_length=66)
    # preferred_attorney is deprecated — all consultations are currently handled by Brannon McKay
    preferred_attorney: Optional[str] = Field(default=None, max_length=50, deprecated=True)

    @field_validator('preferred_attorney')
    @classmethod
    def validate_attorney(cls, v):
        # Ignored — all consultations route to Brannon McKay initially
        return None
        valid_attorneys = ["brannon", "josh", "ben", "ginger", "manoj"]
        v = v.strip().lower()
        if v not in valid_attorneys:
            raise ValueError(f"Invalid attorney. Available: {', '.join(valid_attorneys)}")
        return v

    @field_validator('contact_email')
    @classmethod
    def validate_contact_email(cls, v):
        valid, result = validate_email(v)
        if not valid:
            raise ValueError(result)
        return result

    @field_validator('topic', 'description', 'contact_name')
    @classmethod
    def sanitize_text_fields(cls, v):
        return sanitize_text(v, MAX_DESCRIPTION_LENGTH)


MAX_MESSAGE_LENGTH = 10000
MAX_ATTACHMENT_URLS = 5


class ConsultationMessageRequest(BaseModel):
    """Send a message within an existing consultation thread."""
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    attachments: Optional[list[str]] = Field(default=None, max_length=MAX_ATTACHMENT_URLS)

    @field_validator('message')
    @classmethod
    def sanitize_message(cls, v):
        return sanitize_text(v, MAX_MESSAGE_LENGTH)

    @field_validator('attachments')
    @classmethod
    def validate_attachment_urls(cls, v):
        if v is None:
            return v
        validated = []
        for url in v:
            valid, result = sanitize_url(url)
            if not valid:
                raise ValueError(f"Invalid attachment URL: {result}")
            validated.append(result)
        return validated

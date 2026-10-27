import html
import os
import re
import secrets
import string
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

import psycopg2
import requests
from flask import Flask, jsonify, request
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
COMPANY_EMAIL = os.environ.get("COMPANY_EMAIL", "bookings@exumasportcoast.com")
APPS_SCRIPT_URL = os.environ.get("GOOGLE_APPS_SCRIPT_URL", "")
APPS_SCRIPT_TOKEN = os.environ.get("GOOGLE_APPS_SCRIPT_TOKEN", "")

DB_CONNECT_TIMEOUT = int(os.environ.get("DB_CONNECT_TIMEOUT", "5"))


# --------------------------------------------------------------------------
# Database helpers
# --------------------------------------------------------------------------
def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    # Fail fast instead of hanging Gunicorn's boot / a request worker.
    return psycopg2.connect(
        DATABASE_URL,
        connect_timeout=DB_CONNECT_TIMEOUT,
        application_name="exuma-app",
        options=f"-c statement_timeout={int(os.environ.get('DB_STATEMENT_TIMEOUT_MS', '10000'))}",
    )


def init_db():
    conn = None
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS reservations (
                        id                 BIGSERIAL PRIMARY KEY,
                        reservation_number TEXT UNIQUE NOT NULL,
                        region             TEXT NOT NULL,
                        accommodation      TEXT NOT NULL,
                        check_in           DATE NOT NULL,
                        check_out          DATE NOT NULL,
                        adults             INTEGER NOT NULL,
                        children           INTEGER NOT NULL DEFAULT 0,
                        price              NUMERIC(12, 2) NOT NULL,
                        created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS reservations_created_at_idx
                    ON reservations (created_at DESC)
                """)
    finally:
        if conn:
            conn.close()


# --------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------
def parse_date(value, label):
    """Parse an ISO (YYYY-MM-DD) date, raising ValueError with a friendly message."""
    if value is None or str(value).strip() == "":
        raise ValueError(f"Please provide a valid {label} date.")
    raw = str(value).strip()
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Please provide a valid {label} date in YYYY-MM-DD format.")


def generate_number(prefix="EXS"):
    alphabet = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"{prefix}-{date.today():%y%m%d}-{suffix}"


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def serialize_row(row):
    """Make a psycopg2 RealDictRow JSON-serialisable (Decimal / date / datetime)."""
    out = {}
    for key, value in dict(row).items():
        if isinstance(value, Decimal):
            out[key] = float(value)
        elif isinstance(value, (date, datetime)):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def google_apps_script_send(payload, timeout=10):
    if not APPS_SCRIPT_URL:
        raise RuntimeError("GOOGLE_APPS_SCRIPT_URL is not set")
    body = dict(payload)
    if APPS_SCRIPT_TOKEN:
        body.setdefault("token", APPS_SCRIPT_TOKEN)
    response = requests.post(APPS_SCRIPT_URL, json=body, timeout=timeout)
    response.raise_for_status()
    return response


# --------------------------------------------------------------------------
# Lazy DB init — never block Gunicorn boot
# --------------------------------------------------------------------------
_db_initialized = False


@app.before_request
def ensure_db_initialized():
    global _db_initialized
    if _db_initialized:
        return
    try:
        init_db()
        _db_initialized = True
    except Exception:
        app.logger.exception("Database initialization failed")
        # Don't mark as initialized; /health will report it and it will retry.


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) AS count FROM reservations")
            count = cur.fetchone()["count"]

        return jsonify({
            "success": True,
            "database": "ok",
            "reservations_count": count,
        })

    except Exception:
        app.logger.exception("Health check failed")
        return jsonify({
            "success": False,
            "database": "unavailable",
        }), 503

    finally:
        if conn:
            conn.close()


# --------------------------------------------------------------------------
# Reservations
# --------------------------------------------------------------------------
@app.route("/reserve", methods=["POST"])
def reserve():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = request.form.to_dict()

    region = str(payload.get("region") or "").strip()
    accommodation = str(payload.get("accommodation") or "").strip()
    if not region or not accommodation:
        return jsonify({
            "success": False,
            "error": "Please select a region and accommodation.",
        }), 400

    if len(region) > 120 or len(accommodation) > 160:
        return jsonify({
            "success": False,
            "error": "One or more selection fields are too long.",
        }), 400

    try:
        check_in = parse_date(payload.get("check_in"), "check-in")
        check_out = parse_date(payload.get("check_out"), "check-out")
        adults = int(payload.get("adults") or 2)
        children = int(payload.get("children") or 0)
        nightly_price = Decimal(str(payload.get("price") or "0"))

        if check_out <= check_in:
            raise ValueError("Check-out must be after check-in.")
        if adults < 1 or adults > 30 or children < 0 or children > 30:
            raise ValueError("Please enter a valid number of adults and children.")
        if (not nightly_price.is_finite()
                or nightly_price <= 0
                or nightly_price > Decimal("100000")):
            raise ValueError("The accommodation price is invalid.")
    except (ValueError, TypeError, InvalidOperation) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    nights = (check_out - check_in).days
    if nights < 1:
        return jsonify({
            "success": False,
            "error": "Check-out must be after check-in.",
        }), 400

    total_price = (nightly_price * nights).quantize(Decimal("0.01"))

    conn = None
    try:
        conn = get_connection()
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                row = None
                # Retry a few times in the extremely unlikely event of a number collision.
                for _attempt in range(5):
                    reservation_number = generate_number()
                    cur.execute("""
                        INSERT INTO reservations
                            (reservation_number, region, check_in, check_out, adults, children,
                             accommodation, price, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (reservation_number) DO NOTHING
                        RETURNING *
                    """, (
                        reservation_number, region, check_in, check_out,
                        adults, children, accommodation, total_price,
                    ))
                    row = cur.fetchone()
                    if row:
                        break

                if not row:
                    app.logger.error("Reservation number collision persisted after 5 attempts")
                    return jsonify({
                        "success": False,
                        "error": "We could not create your reservation. Please try again.",
                    }), 500

        return jsonify({
            "success": True,
            "message": "Reservation confirmed.",
            "reservation": serialize_row(row),
        }), 201

    except Exception:
        app.logger.exception("Reservation creation failed")
        return jsonify({
            "success": False,
            "error": "We could not create your reservation right now. Please try again.",
        }), 500

    finally:
        if conn:
            conn.close()


# --------------------------------------------------------------------------
# Boat enquiry
# --------------------------------------------------------------------------
@app.route("/boat-enquiry", methods=["POST"])
def boat_enquiry():
    """Email a boat-rental enquiry; this does not create an accommodation reservation."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = request.form.to_dict()

    name = str(payload.get("name") or payload.get("client_name") or "").strip()
    email = str(payload.get("email") or payload.get("client_email") or "").strip()
    phone = str(payload.get("phone") or payload.get("client_phone") or "").strip()
    boat = str(payload.get("boat") or payload.get("boat_type") or "").strip()
    start_date = str(payload.get("start_date") or payload.get("date") or "").strip()
    end_date = str(payload.get("end_date") or "").strip()
    guests = str(payload.get("guests") or "").strip()
    location = str(payload.get("pickup_location") or payload.get("location") or "").strip()
    message = str(payload.get("message") or payload.get("requirements") or "").strip()

    if not name or not email or not phone:
        return jsonify({
            "success": False,
            "error": "Please provide your name, email address and phone number.",
        }), 400
    if len(name) > 120 or len(email) > 254 or len(phone) > 60:
        return jsonify({
            "success": False,
            "error": "One or more contact fields are too long.",
        }), 400
    if not EMAIL_RE.match(email):
        return jsonify({
            "success": False,
            "error": "Please enter a valid email address.",
        }), 400

    fields = {
        "Customer name": name[:120],
        "Customer email": email[:254],
        "Phone": phone[:60],
        "Boat requested": boat[:160] or "Not specified",
        "Preferred start date": start_date[:40] or "Not specified",
        "Preferred end date": end_date[:40] or "Not specified",
        "Number of guests": guests[:20] or "Not specified",
        "Pickup/location": location[:200] or "Not specified",
        "Additional requirements": message[:3000] or "None provided",
    }

    def safe(value):
        return html.escape(str(value if value is not None else ""))

    rows = "".join(
        f'<tr><th align="left" style="padding:10px;border-bottom:1px solid #e5ecef">{safe(key)}</th>'
        f'<td style="padding:10px;border-bottom:1px solid #e5ecef;white-space:pre-wrap">{safe(value)}</td></tr>'
        for key, value in fields.items()
    )
    plain = "New boat rental enquiry\n\n" + "\n".join(
        f"{key}: {value}" for key, value in fields.items()
    )
    body_html = f"""<!doctype html><html><body style="font-family:Arial,sans-serif;color:#173b43;background:#f5fbfc;padding:20px">
    <div style="max-width:680px;margin:auto;background:#fff;border-radius:12px;padding:24px">
    <h2 style="color:#006d77">New Boat Rental Enquiry</h2>
    <p>A customer submitted a boat rental enquiry through the Exuma Sport Coast Service website.</p>
    <table style="width:100%;border-collapse:collapse">{rows}</table>
    </div></body></html>"""

    try:
        google_apps_script_send({
            # The existing Apps Script handler uses this action for email delivery.
            "action": "payment_request",
            "to": COMPANY_EMAIL,
            "replyTo": email,
            "subject": f"New Boat Rental Enquiry - {fields['Customer name']}",
            "message": plain,
            "htmlBody": body_html,
            "enquiry": fields,
        })
        return jsonify({
            "success": True,
            "message": "Your boat rental enquiry has been sent. We will contact you soon.",
        }), 200

    except Exception:
        app.logger.exception("Boat enquiry email failed")
        return jsonify({
            "success": False,
            "error": "We could not send your enquiry right now. Please try again later or contact the business by email.",
        }), 502


# --------------------------------------------------------------------------
# CORS
# --------------------------------------------------------------------------
@app.after_request
def add_cors_headers(response):
    # Static frontend is hosted separately on Netlify. Restrict browser access to known origins.
    origin = request.headers.get("Origin", "")
    allowed_origins = {
        "https://exumasportaccomodation.netlify.app",
        "https://albertoo404.github.io",
    }
    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Migration-Token"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/<path:unused_path>", methods=["OPTIONS"])
def options_preflight(unused_path):
    return ("", 204)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
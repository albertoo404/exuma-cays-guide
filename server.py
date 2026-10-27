import html
import os
import re
import secrets
import string
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import psycopg2
import requests
from flask import Flask, jsonify, request
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# --------------------------------------------------------------------------
# Config — Apps Script URL resolves from either env var name
# --------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Older working file used GOOGLE_APPS_SCRIPTURL (no underscore before URL).
# Newer envs may have GOOGLE_APPS_SCRIPT_URL. Accept both.
APPS_SCRIPT_URL = (
    os.environ.get("GOOGLE_APPS_SCRIPTURL")
    or os.environ.get("GOOGLE_APPS_SCRIPT_URL")
    or ""
)
APPS_SCRIPT_TOKEN = os.environ.get("GOOGLE_APPS_SCRIPT_TOKEN", "")

# Default matches the address the older working file hardcoded.
COMPANY_EMAIL = os.environ.get("COMPANY_EMAIL", "exumaaccomodations@gmail.com")

DB_CONNECT_TIMEOUT = int(os.environ.get("DB_CONNECT_TIMEOUT", "5"))


# --------------------------------------------------------------------------
# Database helpers
# --------------------------------------------------------------------------
def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
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
                cur.execute("""
                    ALTER TABLE reservations
                      ADD COLUMN IF NOT EXISTS client_name  TEXT,
                      ADD COLUMN IF NOT EXISTS client_phone TEXT,
                      ADD COLUMN IF NOT EXISTS client_email TEXT
                """)
    finally:
        if conn:
            conn.close()


# --------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------
def parse_date(value, label):
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
    out = {}
    for key, value in dict(row).items():
        if isinstance(value, Decimal):
            out[key] = float(value)
        elif isinstance(value, (date, datetime)):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def google_apps_script_send(payload, timeout=30, check_success=False):
    """Forward a payload to the Google Apps Script webhook.

    Matches the older working file's behavior:
      - allow_redirects=True (Apps Script 302s to googleusercontent.com)
      - timeout=30 (Gmail send can take 10-20s under load)
      - parses the JSON response and optionally requires success=True
    """
    if not APPS_SCRIPT_URL:
        raise RuntimeError(
            "GOOGLE_APPS_SCRIPTURL / GOOGLE_APPS_SCRIPT_URL is not configured."
        )

    body = dict(payload)
    if APPS_SCRIPT_TOKEN and "token" not in body:
        body["token"] = APPS_SCRIPT_TOKEN

    response = requests.post(
        APPS_SCRIPT_URL,
        json=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=timeout,
        allow_redirects=True,
    )

    app.logger.info(
        "GOOGLE APPS SCRIPT FINAL RESPONSE: %s %s",
        response.status_code,
        response.text[:1000],
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Google Apps Script returned HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    try:
        result = response.json() if response.text else {}
    except Exception:
        raise RuntimeError(
            "Google Apps Script did not return valid JSON: "
            + response.text[:500]
        )

    if check_success and isinstance(result, dict) and not result.get("success"):
        raise RuntimeError(
            "Google Apps Script rejected the request: "
            + str(result.get("error", "Unknown error"))
        )

    return result


# --------------------------------------------------------------------------
# Lazy DB init
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
            "apps_script_configured": bool(APPS_SCRIPT_URL),
            "company_email": COMPANY_EMAIL,
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
# Reservation lookups & customer updates
# --------------------------------------------------------------------------
@app.route("/reservation-data/<number>", methods=["GET"])
def reservation_data(number):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM reservations WHERE reservation_number = %s",
                (number,),
            )
            row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Reservation not found."}), 404
        return jsonify(serialize_row(row)), 200
    except Exception:
        app.logger.exception("reservation-data failed")
        return jsonify({"success": False, "error": "Server error."}), 500
    finally:
        if conn:
            conn.close()


@app.route("/update-customer/<number>", methods=["POST", "OPTIONS"])
def update_customer(number):
    if request.method == "OPTIONS":
        return ("", 204)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = request.form.to_dict()

    name = str(payload.get("client_name") or "").strip()[:120]
    phone = str(payload.get("client_phone") or "").strip()[:60]
    email = str(payload.get("client_email") or "").strip()[:254]

    if not name or not phone:
        return jsonify({
            "success": False,
            "error": "Please provide your name, phone number and a valid email address.",
        }), 400
    if not EMAIL_RE.match(email):
        return jsonify({
            "success": False,
            "error": "Please provide a valid email address.",
        }), 400

    conn = None
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE reservations "
                    "SET client_name = %s, client_phone = %s, client_email = %s "
                    "WHERE reservation_number = %s",
                    (name, phone, email, number),
                )
                if cur.rowcount == 0:
                    return jsonify({
                        "success": False,
                        "error": "Reservation not found.",
                    }), 404
        return jsonify({
            "success": True,
            "message": "Customer details saved successfully.",
        }), 200
    except Exception:
        app.logger.exception("update-customer failed")
        return jsonify({"success": False, "error": "Server error."}), 500
    finally:
        if conn:
            conn.close()


# --------------------------------------------------------------------------
# Payment request — rich HTML body, real success/failure
# --------------------------------------------------------------------------
def build_payment_request_email(data):
    """Build the plain + HTML bodies for the payment-request notification.
    Mirrors the layout used by the older working file so the recipient
    sees the same colourful template."""
    customer_name = (data.get("client_name") or "Customer").strip()
    customer_email = (data.get("client_email") or "").strip()
    customer_phone = (data.get("client_phone") or "Not provided").strip()

    reservation = data.get("reservation_number") or "—"
    accommodation = data.get("accommodation") or "—"
    region = data.get("region") or "—"
    check_in = data.get("check_in") or "—"
    check_out = data.get("check_out") or "—"
    adults = data.get("adults", 0)
    children = data.get("children", 0)

    try:
        total = float(data.get("price") or 0)
    except (ValueError, TypeError):
        total = 0.0

    deposit = total * 0.50

    def esc(value):
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#039;")
        )

    subject = f"Payment Details Request - Reservation {reservation}"

    body_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width">
<title>Payment Details Request</title>
</head>
<body style="margin:0;padding:25px 10px;background:#eef8fb;font-family:Arial,Helvetica,sans-serif;color:#173b43;">
<div style="max-width:650px;margin:auto;background:#ffffff;border-radius:18px;overflow:hidden;">
<div style="background:#006d77;padding:30px 20px;text-align:center;color:#ffffff;">
<h1 style="margin:0;font-size:30px;">EXUMA SPORTS ACCOMMODATIONS</h1>
<p style="margin:8px 0 0;font-size:15px;">Payment Details Request</p>
</div>
<div style="padding:30px 25px;">
<h2 style="color:#006d77;margin-top:0;">New Payment Request</h2>
<p>A customer has requested payment details for the following reservation.</p>
<div style="background:#f1fbfc;border-left:5px solid #00a6a6;padding:18px;margin:20px 0;border-radius:8px;">
<p><strong>Reservation:</strong> {esc(reservation)}</p>
<p><strong>Customer:</strong> {esc(customer_name)}</p>
<p><strong>Email:</strong> {esc(customer_email)}</p>
<p><strong>Phone:</strong> {esc(customer_phone)}</p>
<p><strong>Accommodation:</strong> {esc(accommodation)}</p>
<p><strong>Region:</strong> {esc(region)}</p>
<p><strong>Check-in:</strong> {esc(check_in)}</p>
<p><strong>Check-out:</strong> {esc(check_out)}</p>
<p><strong>Adults:</strong> {esc(adults)}</p>
<p><strong>Children:</strong> {esc(children)}</p>
</div>
<div style="background:#fff8e7;border-radius:10px;padding:18px;margin-top:20px;">
<p style="margin:5px 0;"><strong>Total accommodation price:</strong> ${total:,.2f}</p>
<p style="margin:5px 0;"><strong>50% deposit:</strong> ${deposit:,.2f}</p>
</div>
<p style="margin-top:25px;color:#555;font-size:14px;">
Please provide the appropriate payment instructions or payment link to the customer using their contact information above.
</p>
</div>
<div style="background:#023047;color:white;padding:18px;text-align:center;font-size:13px;">
Exuma Cays Guide · Exuma, Bahamas
</div>
</div>
</body>
</html>
"""

    plain_message = f"""Payment Details Request

Reservation: {reservation}
Customer: {customer_name}
Email: {customer_email}
Phone: {customer_phone}
Accommodation: {accommodation}
Region: {region}
Check-in: {check_in}
Check-out: {check_out}
Adults: {adults}
Children: {children}

Total accommodation price: ${total:,.2f}
50% deposit: ${deposit:,.2f}

Please provide the customer with the appropriate payment instructions or payment link.
"""

    return subject, plain_message, body_html


@app.route("/request-payment-details/<number>", methods=["POST", "OPTIONS"])
def request_payment_details(number):
    if request.method == "OPTIONS":
        return ("", 204)

    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM reservations WHERE reservation_number = %s",
                (number,),
            )
            row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Reservation not found."}), 404

        data = serialize_row(row)
        data["reservation_number"] = number

        customer_name = (data.get("client_name") or "").strip()
        customer_phone = (data.get("client_phone") or "").strip()
        customer_email = (data.get("client_email") or "").strip()

        if not customer_name or not customer_phone or not customer_email:
            return jsonify({
                "success": False,
                "error": (
                    "Please enter your name, phone number and email "
                    "before requesting payment details."
                ),
            }), 400

        subject, plain_message, body_html = build_payment_request_email(data)

        # Payload matches the older working file exactly.
        payload = {
            "action": "payment_request",
            "to": COMPANY_EMAIL,
            "subject": subject,
            "message": plain_message,
            "htmlBody": body_html,
        }

        try:
            google_apps_script_send(payload, timeout=30, check_success=True)
        except Exception as exc:
            app.logger.exception("Payment request email failed")
            return jsonify({
                "success": False,
                "error": f"Email delivery failed — {exc}",
            }), 502

        return jsonify({
            "success": True,
            "message": "Your payment-details request has been sent successfully.",
            "reservation_number": number,
        }), 200

    except Exception:
        app.logger.exception("request-payment-details failed")
        return jsonify({"success": False, "error": "Server error."}), 500
    finally:
        if conn:
            conn.close()


# --------------------------------------------------------------------------
# Boat enquiry — unchanged
# --------------------------------------------------------------------------
@app.route("/boat-enquiry", methods=["POST"])
def boat_enquiry():
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
            "action": "payment_request",
            "to": COMPANY_EMAIL,
            "replyTo": email,
            "subject": f"New Boat Rental Enquiry - {fields['Customer name']}",
            "message": plain,
            "htmlBody": body_html,
            "enquiry": fields,
        }, timeout=30, check_success=False)
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

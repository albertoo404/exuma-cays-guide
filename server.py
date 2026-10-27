import os
import html
import secrets
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import psycopg2
from psycopg2.extras import RealDictCursor
import requests
from flask import Flask, jsonify, request, redirect, url_for

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

COMPANY_EMAIL = os.environ.get("COMPANY_EMAIL", "exumaaccomodations@gmail.com")
GOOGLE_APPS_SCRIPT_URL = os.environ.get("GOOGLE_APPS_SCRIPTURL", "").strip()
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
MIGRATION_TOKEN = os.environ.get("MIGRATION_TOKEN", "").strip()


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is not configured.")
    return psycopg2.connect(DATABASE_URL, sslmode="require", connect_timeout=10)


def init_db():
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS reservations (
                        id SERIAL PRIMARY KEY,
                        reservation_number VARCHAR(40) UNIQUE NOT NULL,
                        region TEXT,
                        check_in DATE,
                        check_out DATE,
                        adults INTEGER NOT NULL DEFAULT 2,
                        children INTEGER NOT NULL DEFAULT 0,
                        accommodation TEXT,
                        price NUMERIC(12,2) NOT NULL DEFAULT 0,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        client_name TEXT,
                        client_phone TEXT,
                        client_email TEXT
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS reservations_created_at_idx ON reservations (created_at DESC)")
                # Support databases created before customer fields were added.
                for column, sql_type in (
                    ("client_name", "TEXT"), ("client_phone", "TEXT"), ("client_email", "TEXT"),
                    ("region", "TEXT"), ("check_in", "DATE"), ("check_out", "DATE"),
                    ("adults", "INTEGER DEFAULT 2"), ("children", "INTEGER DEFAULT 0"),
                    ("accommodation", "TEXT"), ("price", "NUMERIC(12,2)"),
                    ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                ):
                    cur.execute(f"ALTER TABLE reservations ADD COLUMN IF NOT EXISTS {column} {sql_type}")
    finally:
        conn.close()


def generate_number():
    return f"EXM-{datetime.utcnow():%Y%m%d}-{secrets.randbelow(9000) + 1000}"


def google_apps_script_send(payload):
    if not GOOGLE_APPS_SCRIPT_URL:
        raise RuntimeError("GOOGLE_APPS_SCRIPTURL environment variable is not configured.")
    response = requests.post(GOOGLE_APPS_SCRIPT_URL, json=payload, timeout=25)
    response.raise_for_status()
    try:
        result = response.json()
    except ValueError:
        result = {"success": True, "response": response.text[:500]}
    if isinstance(result, dict) and result.get("success") is False:
        raise RuntimeError("Google Apps Script reported that the email was not sent.")
    return result


def parse_date(value, field_name):
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"Please provide a valid {field_name} date in YYYY-MM-DD format.")


def reservation_dict(row):
    if not row:
        return None
    result = dict(row)
    for key in ("check_in", "check_out"):
        if result.get(key) is not None:
            result[key] = result[key].isoformat()
    if result.get("created_at") is not None:
        result["created_at"] = result["created_at"].isoformat()
    if result.get("price") is not None:
        result["price"] = float(result["price"])
    return result


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "Exuma Sport Coast Service API",
        "success": True,
        "health": "/health"
    })


@app.route("/health", methods=["GET"])
def health():
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM reservations")
            count = cur.fetchone()[0]
        return jsonify({"success": True, "database": "PostgreSQL", "reservations_count": count})
    except Exception:
        app.logger.exception("Health check failed")
        return jsonify({"success": False, "database": "unavailable"}), 503
    finally:
        if conn:
            conn.close()


@app.route("/reserve", methods=["POST"])
def reserve():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = request.form.to_dict()

    region = str(payload.get("region") or "").strip()
    accommodation = str(payload.get("accommodation") or "").strip()
    if not region or not accommodation:
        return jsonify({"success": False, "error": "Please select a region and accommodation."}), 400

    try:
        check_in = parse_date(payload.get("check_in"), "check-in")
        check_out = parse_date(payload.get("check_out"), "check-out")
        adults = int(payload.get("adults", 2))
        children = int(payload.get("children", 0))
        nightly_price = Decimal(str(payload.get("price", "0")))
        if check_out <= check_in:
            raise ValueError("Check-out must be after check-in.")
        if adults < 1 or adults > 30 or children < 0 or children > 30:
            raise ValueError("Please enter a valid number of adults and children.")
        if not nightly_price.is_finite() or nightly_price <= 0 or nightly_price > Decimal("100000"):
            raise ValueError("The accommodation price is invalid.")
    except (ValueError, InvalidOperation) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    nights = (check_out - check_in).days
    total_price = (nightly_price * nights).quantize(Decimal("0.01"))
    conn = None
    try:
        conn = get_connection()
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                reservation_number = generate_number()
                # Retry a few times in the extremely unlikely event of a number collision.
                for attempt in range(5):
                    cur.execute("""
                        INSERT INTO reservations
                            (reservation_number, region, check_in, check_out, adults, children,
                             accommodation, price, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (reservation_number) DO NOTHING
                        RETURNING *
                    """, (reservation_number, region, check_in, check_out, adults, children,
                          accommodation, total_price))
                    row = cur.fetchone()
                    if row:
                        break
                    reservation_number = generate_number()
                if not row:
                    raise RuntimeError("Could not generate a unique reservation number.")
        result = reservation_dict(row)
        # JSON clients receive the record; traditional HTML form submissions go to the receipt page.
        if request.is_json:
            return jsonify({"success": True, "reservation": result}), 201
        return redirect(url_for("reservation_details", number=reservation_number))
    except Exception:
        app.logger.exception("Reservation creation failed")
        return jsonify({"success": False, "error": "We could not create your reservation right now. Please try again."}), 500
    finally:
        if conn:
            conn.close()


@app.route("/reservation/<number>", methods=["GET"])
def reservation_details(number):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM reservations WHERE reservation_number = %s", (number,))
            row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Reservation not found."}), 404
        return jsonify({"success": True, "reservation": reservation_dict(row)})
    except Exception:
        app.logger.exception("Could not load reservation")
        return jsonify({"success": False, "error": "Could not load reservation details."}), 500
    finally:
        if conn:
            conn.close()


@app.route("/update-customer/<number>", methods=["POST"])
def update_customer(number):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = request.form.to_dict()
    name = str(payload.get("client_name") or payload.get("name") or "").strip()
    phone = str(payload.get("client_phone") or payload.get("phone") or "").strip()
    email = str(payload.get("client_email") or payload.get("email") or "").strip()

    if not name or not phone or not email:
        return jsonify({"success": False, "error": "Please provide your name, phone number and email address."}), 400
    if len(name) > 120 or len(phone) > 60 or len(email) > 254 or "@" not in email:
        return jsonify({"success": False, "error": "Please check your contact details and try again."}), 400

    conn = None
    try:
        conn = get_connection()
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    UPDATE reservations
                    SET client_name = %s, client_phone = %s, client_email = %s
                    WHERE reservation_number = %s
                    RETURNING *
                """, (name, phone, email, number))
                row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Reservation not found."}), 404
        return jsonify({"success": True, "reservation": reservation_dict(row)})
    except Exception:
        app.logger.exception("Could not update customer details")
        return jsonify({"success": False, "error": "Could not save customer details right now."}), 500
    finally:
        if conn:
            conn.close()


@app.route("/request-payment-details/<number>", methods=["POST"])
def request_payment_details(number):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM reservations WHERE reservation_number = %s", (number,))
            row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Reservation not found."}), 404
        reservation = reservation_dict(row)
        if not reservation.get("client_name") or not reservation.get("client_email") or not reservation.get("client_phone"):
            return jsonify({"success": False, "error": "Please save your name, phone number and email before requesting payment details."}), 400

        total = Decimal(str(reservation["price"]))
        deposit = (total * Decimal("0.50")).quantize(Decimal("0.01"))
        safe = lambda value: html.escape(str(value if value is not None else ""))
        subject = f"Payment details request — {reservation['reservation_number']}"
        plain = (
            "EXUMA SPORTS ACCOMMODATIONS\n\n"
            f"Reservation: {reservation['reservation_number']}\n"
            f"Customer: {reservation['client_name']}\n"
            f"Email: {reservation['client_email']}\n"
            f"Phone: {reservation['client_phone']}\n"
            f"Accommodation: {reservation['accommodation']}\n"
            f"Region: {reservation['region']}\n"
            f"Check-in: {reservation['check_in']}\n"
            f"Check-out: {reservation['check_out']}\n"
            f"Total price: ${total:.2f}\n"
            f"Requested 50% deposit: ${deposit:.2f}\n\n"
            "Please send the customer the applicable payment details."
        )
        body_html = f"""<!doctype html><html><body style="font-family:Arial,sans-serif;color:#173b43;background:#f5fbfc;padding:20px">
        <div style="max-width:680px;margin:auto;background:#fff;border-radius:12px;padding:24px">
        <h2 style="color:#006d77">EXUMA SPORTS ACCOMMODATIONS</h2>
        <p>A customer has requested payment details for a reservation.</p>
        <table style="width:100%;border-collapse:collapse">
        <tr><th align="left">Reservation</th><td>{safe(reservation['reservation_number'])}</td></tr>
        <tr><th align="left">Customer</th><td>{safe(reservation['client_name'])}</td></tr>
        <tr><th align="left">Email</th><td>{safe(reservation['client_email'])}</td></tr>
        <tr><th align="left">Phone</th><td>{safe(reservation['client_phone'])}</td></tr>
        <tr><th align="left">Accommodation</th><td>{safe(reservation['accommodation'])}</td></tr>
        <tr><th align="left">Region</th><td>{safe(reservation['region'])}</td></tr>
        <tr><th align="left">Check-in</th><td>{safe(reservation['check_in'])}</td></tr>
        <tr><th align="left">Check-out</th><td>{safe(reservation['check_out'])}</td></tr>
        <tr><th align="left">Total price</th><td>${total:.2f}</td></tr>
        <tr><th align="left">50% deposit</th><td>${deposit:.2f}</td></tr>
        </table>
        <p>Please contact the customer with payment instructions.</p></div></body></html>"""
        google_apps_script_send({
            "action": "payment_request",
            "to": COMPANY_EMAIL,
            "replyTo": reservation["client_email"],
            "subject": subject,
            "message": plain,
            "htmlBody": body_html,
            "reservation": reservation,
            "deposit": float(deposit)
        })
        return jsonify({"success": True, "message": "Payment details have been requested. We will contact you soon."})
    except Exception:
        app.logger.exception("Payment details request failed")
        return jsonify({"success": False, "error": "We could not send the payment request right now. Please try again later."}), 502
    finally:
        if conn:
            conn.close()


@app.route("/migrate-reservations", methods=["POST"])
def migrate_reservations():
    # Keep this endpoint protected. Set MIGRATION_TOKEN in Render and send it
    # as the X-Migration-Token request header when performing a trusted migration.
    if not MIGRATION_TOKEN or request.headers.get("X-Migration-Token") != MIGRATION_TOKEN:
        return jsonify({"success": False, "error": "Unauthorized."}), 401
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify({"success": False, "error": "Expected a JSON array of reservations."}), 400
    if len(data) > 5000:
        return jsonify({"success": False, "error": "Too many records in one migration request."}), 413

    conn = None
    inserted = skipped = 0
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                for item in data:
                    if not isinstance(item, dict) or not item.get("reservation_number"):
                        skipped += 1
                        continue
                    cur.execute("""
                        INSERT INTO reservations
                        (reservation_number, region, check_in, check_out, adults, children,
                         accommodation, price, created_at, client_name, client_phone, client_email)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (reservation_number) DO NOTHING
                    """, (item.get("reservation_number"), item.get("region"), item.get("check_in"),
                          item.get("check_out"), item.get("adults", 2), item.get("children", 0),
                          item.get("accommodation"), item.get("price", 0), item.get("created_at") or datetime.utcnow(),
                          item.get("client_name"), item.get("client_phone"), item.get("client_email")))
                    if cur.rowcount == 1:
                        inserted += 1
                    else:
                        skipped += 1
        return jsonify({"success": True, "received": len(data), "inserted": inserted,
                        "skipped_existing": skipped})
    except Exception:
        if conn:
            conn.rollback()
        app.logger.exception("Reservation migration failed")
        return jsonify({"success": False, "error": "Migration failed."}), 500
    finally:
        if conn:
            conn.close()


@app.route("/boat-enquiry", methods=["POST"])
def boat_enquiry():
    """Email a boat-rental enquiry through Google Apps Script; no reservation is created."""
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
        return jsonify({"success": False, "error": "Please provide your name, email address and phone number."}), 400
    if len(name) > 120 or len(email) > 254 or len(phone) > 60:
        return jsonify({"success": False, "error": "One or more contact fields are too long."}), 400
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        return jsonify({"success": False, "error": "Please enter a valid email address."}), 400

    fields = {
        "Customer name": name[:120], "Customer email": email[:254], "Phone": phone[:60],
        "Boat requested": boat[:160] or "Not specified",
        "Preferred start date": start_date[:40] or "Not specified",
        "Preferred end date": end_date[:40] or "Not specified",
        "Number of guests": guests[:20] or "Not specified",
        "Pickup/location": location[:200] or "Not specified",
        "Additional requirements": message[:3000] or "None provided"
    }
    subject = f"New Boat Rental Enquiry — {fields['Customer name']}"
    plain = "New boat rental enquiry\n\n" + "\n".join(f"{key}: {value}" for key, value in fields.items())
    safe = lambda value: html.escape(str(value))
    rows = "".join(
        f"<tr><th style='text-align:left;padding:10px;border-bottom:1px solid #e5ecef'>{safe(key)}</th>"
        f"<td style='padding:10px;border-bottom:1px solid #e5ecef;white-space:pre-wrap'>{safe(value)}</td></tr>"
        for key, value in fields.items()
    )
    body_html = f"""<!doctype html><html><body style="font-family:Arial,sans-serif;color:#173b43;background:#f5fbfc;padding:20px">
    <div style="max-width:680px;margin:auto;background:#fff;border-radius:12px;padding:24px">
    <h2 style="color:#006d77">New Boat Rental Enquiry</h2>
    <p>A customer submitted a boat rental enquiry through the Exuma Sport Coast Service website.</p>
    <table style="width:100%;border-collapse:collapse">{rows}</table>
    <p style="margin-top:20px;font-size:13px;color:#607d86">Reply directly to the customer using the contact details above.</p>
    </div></body></html>"""

    try:
        google_apps_script_send({
            "action": "payment_request",
            "to": COMPANY_EMAIL,
            "replyTo": email,
            "subject": subject,
            "message": plain,
            "htmlBody": body_html,
            "enquiry": fields
        })
        app.logger.info("Boat enquiry email accepted by Apps Script.")
        return jsonify({"success": True, "message": "Your boat rental enquiry has been sent. We will contact you soon."}), 200
    except Exception:
        app.logger.exception("Boat enquiry email failed")
        return jsonify({"success": False, "error": "We could not send your enquiry right now. Please try again later or contact the business by email."}), 502


# Do not let a missing/misconfigured database prevent the import error from being obvious in logs.
try:
    init_db()
except Exception:
    app.logger.exception("Database initialization failed; check DATABASE_URL and database availability.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)

from flask import Flask, request, redirect, send_from_directory, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
from datetime import datetime
import secrets
import os
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)
CORS(app, origins=[
    "https://albertoo404.github.io",
    "https://exumasportaccomodation.netlify.app"
])

BASE = Path(__file__).resolve().parent
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not configured.")
RECEIPTS = BASE / "reservations"
RECEIPTS.mkdir(exist_ok=True)

def init_db():
    conn = psycopg2.connect(DATABASE_URL)

    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reservations (
                    id SERIAL PRIMARY KEY,
                    reservation_number TEXT UNIQUE NOT NULL,
                    region TEXT NOT NULL,
                    check_in TEXT NOT NULL,
                    check_out TEXT NOT NULL,
                    adults INTEGER NOT NULL,
                    children INTEGER NOT NULL,
                    accommodation TEXT NOT NULL,
                    price DOUBLE PRECISION NOT NULL,
                    created_at TEXT NOT NULL,
                    client_name TEXT,
                    client_phone TEXT,
                    client_email TEXT
                )
            """)

        conn.commit()
        print("PostgreSQL database initialized successfully.")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def generate_number():
    date = datetime.now().strftime("%Y%m%d")
    return f"EXM-{date}-{secrets.randbelow(9000) + 1000}"

def create_receipt(data):
    number = data["reservation_number"]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reservation {number} | Exuma Sport Coast Service</title>

<style>
body {{
    margin: 0;
    padding: 25px 15px;
    background: #f5fbfc;
    font-family: Arial, sans-serif;
    color: #173b43;
}}

.receipt {{
    max-width: 600px;
    margin: auto;
    background: white;
    padding: 30px;
    border-radius: 14px;
    box-shadow: 0 8px 30px rgba(0,0,0,.12);
}}

.header {{
    text-align: center;
    border-bottom: 2px solid #023047;
    padding-bottom: 18px;
}}

.header img {{
    width: 70px;
    height: 70px;
    object-fit: contain;
}}

.header h1 {{
    color: #006d77;
    margin: 8px 0;
    font-size: 24px;
}}

.reference {{
    margin: 20px 0;
    padding: 12px;
    text-align: center;
    background: #eef9fa;
}}

.detail {{
    display: flex;
    justify-content: space-between;
    gap: 20px;
    padding: 11px 0;
    border-bottom: 1px solid #eee;
}}

.label {{
    color: #607d86;
}}

.note {{
    margin-top: 20px;
    padding: 14px;
    background: #f5f5f5;
    font-size: 13px;
}}

.footer {{
    text-align: center;
    margin-top: 25px;
    padding-top: 15px;
    border-top: 1px solid #ddd;
    font-size: 12px;
    color: #777;
}}

button {{
    display: block;
    margin: 20px auto 0;
    padding: 11px 25px;
    border: 0;
    border-radius: 22px;
    background: #023047;
    color: white;
    cursor: pointer;
}}

@media print {{
    body {{
        background: white;
    }}

    .receipt {{
        box-shadow: none;
    }}

    button {{
        display: none;
    }}
}}
</style>
</head>

<body>

<div class="receipt">

<div class="header">
    <img src="https://exuma-cays-guide-api.onrender.com/images/exumalogo.jpg"
         alt="Exuma Sport Coast Service">
    <h1>Exuma Sport Coast Service</h1>
    <p>Accommodation Reservation Receipt</p>
</div>

<div class="reference">
    Reservation Number<br>
    <strong>{number}</strong>
</div>

<div class="detail">
    <span class="label">Region</span>
    <strong>{data["region"]}</strong>
</div>

<div class="detail">
    <span class="label">Check-in</span>
    <strong>{data["check_in"]}</strong>
</div>

<div class="detail">
    <span class="label">Check-out</span>
    <strong>{data["check_out"]}</strong>
</div>

<div class="detail">
    <span class="label">Adults</span>
    <strong>{data["adults"]}</strong>
</div>

<div class="detail">
    <span class="label">Children</span>
    <strong>{data["children"]}</strong>
</div>

<div class="detail">
    <span class="label">Total Clients</span>
    <strong>{data["adults"] + data["children"]}</strong>
</div>

<div class="detail">
    <span class="label">Accommodation</span>
    <strong>{data["accommodation"]}</strong>
</div>

<div class="detail">
    <span class="label">Number of Nights</span>
    <strong>{data.get("nights", 0)}</strong>
</div>

<div class="detail">
    <span class="label">Total</span>
    <strong>USD {data["price"]:.2f}</strong>
</div>

<div class="detail">
    <span class="label">Reserved</span>
    <strong>{data["created_at"]}</strong>
</div>

<div class="note">
    Please keep this receipt for your reservation records.
    For assistance contact
    <strong>exumaaccomodations@gmail.com</strong>.
</div>

<button onclick="window.print()">Print / Save PDF</button>

<div class="footer">
    © 2026 Exuma Sport Coast Service · Exuma, Bahamas
</div>

</div>

</body>
</html>
"""

    (RECEIPTS / f"{number}.html").write_text(html)

@app.route("/")
def home():
    return send_from_directory(BASE, "index.html")

@app.route("/accommodations.html")
def accommodations():
    return send_from_directory(BASE, "accommodations.html")

@app.route("/<path:filename>")
def website_files(filename):
    file_path = BASE / filename

    if file_path.is_file():
        return send_from_directory(BASE, filename)

    return "File not found", 404

@app.route("/reserve", methods=["POST"])
def reserve():
    region = request.form.get("region", "").strip()
    check_in = request.form.get("check_in", "").strip()
    check_out = request.form.get("check_out", "").strip()
    accommodation = request.form.get("accommodation", "").strip()
    client_name = request.form.get("client_name", "").strip()
    client_phone = request.form.get("client_phone", "").strip()
    client_email = request.form.get("client_email", "").strip()

    try:
        adults = max(1, int(request.form.get("adults", "1")))
        children = max(0, int(request.form.get("children", "0")))
        nightly_price = float(request.form.get("price", "0"))

        check_in_date = datetime.strptime(
            check_in, "%Y-%m-%d"
        ).date()

        check_out_date = datetime.strptime(
            check_out, "%Y-%m-%d"
        ).date()

        nights = (check_out_date - check_in_date).days

    except (ValueError, TypeError):
        return "Invalid reservation information", 400

    if nights <= 0:
        return "Check-out must be after check-in", 400

    if nightly_price < 0:
        return "Invalid accommodation price", 400

    # Final accommodation price = nights × nightly price
    price = nightly_price * nights

    
    number = generate_number()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data = {
        "reservation_number": number,
        "region": region,
        "check_in": check_in,
        "check_out": check_out,
        "adults": adults,
        "children": children,
        "accommodation": accommodation,
        "price": price,
        "nights": nights,
        "client_name": client_name or None,
        "client_phone": client_phone or None,
        "client_email": client_email or None,
        "created_at": created_at
    }

    conn = psycopg2.connect(DATABASE_URL)

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO reservations
                (
                    reservation_number,
                    region,
                    check_in,
                    check_out,
                    adults,
                    children,
                    accommodation,
                    price,
                    client_name,
                    client_phone,
                    client_email,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                number,
                region,
                check_in,
                check_out,
                adults,
                children,
                accommodation,
                price,
                client_name or None,
                client_phone or None,
                client_email or None,
                created_at
            ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    create_receipt(data)

    return redirect(f"/reservation/{number}")


@app.route("/reservation/<number>")
def receipt(number):
    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM reservations WHERE reservation_number = %s",
                (number,)
            )
            row = cur.fetchone()

    finally:
        conn.close()

    if not row:
        return "Reservation not found", 404

    data = dict(row)

    try:
        check_in_date = datetime.strptime(
            data["check_in"], "%Y-%m-%d"
        ).date()

        check_out_date = datetime.strptime(
            data["check_out"], "%Y-%m-%d"
        ).date()

        data["nights"] = (
            check_out_date - check_in_date
        ).days

    except (ValueError, TypeError):
        data["nights"] = 0

    create_receipt(data)

    return send_from_directory(
        RECEIPTS,
        f"{number}.html"
    )





def send_payment_request_email(data):
    """
    Send a colourful HTML payment-details request
    through Google Apps Script.
    """

    company_email = "exumaaccomodations@gmail.com"

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

    subject = f"Payment Details Request - Reservation {reservation}"

    def escape_html(value):
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#039;")
        )

    html = f"""<!DOCTYPE html>
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

<p><strong>Reservation:</strong> {escape_html(reservation)}</p>
<p><strong>Customer:</strong> {escape_html(customer_name)}</p>
<p><strong>Email:</strong> {escape_html(customer_email)}</p>
<p><strong>Phone:</strong> {escape_html(customer_phone)}</p>
<p><strong>Accommodation:</strong> {escape_html(accommodation)}</p>
<p><strong>Region:</strong> {escape_html(region)}</p>
<p><strong>Check-in:</strong> {escape_html(check_in)}</p>
<p><strong>Check-out:</strong> {escape_html(check_out)}</p>
<p><strong>Adults:</strong> {escape_html(adults)}</p>
<p><strong>Children:</strong> {escape_html(children)}</p>

</div>

<div style="background:#fff8e7;border-radius:10px;padding:18px;margin-top:20px;">

<p style="margin:5px 0;">
<strong>Total accommodation price:</strong> ${total:,.2f}
</p>

<p style="margin:5px 0;">
<strong>50% deposit:</strong> ${deposit:,.2f}
</p>

</div>

<p style="margin-top:25px;color:#555;font-size:14px;">
Please provide the appropriate payment instructions or payment link
to the customer using their contact information above.
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

    google_apps_script_url = os.environ.get("GOOGLE_APPS_SCRIPT_URL")

    if not google_apps_script_url:
        raise RuntimeError("GOOGLE_APPS_SCRIPT_URL is not configured.")

    payload = {
        "action": "payment_request",
        "to": company_email,
        "subject": subject,
        "message": plain_message,
        "htmlBody": html
    }

    try:
        response = requests.post(
            google_apps_script_url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=30
        )

        print(
            "GOOGLE APPS SCRIPT RESPONSE:",
            response.status_code,
            response.text[:1000]
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Google Apps Script returned HTTP "
                f"{response.status_code}: {response.text[:500]}"
            )

        try:
            result = response.json()
        except Exception:
            raise RuntimeError(
                "Google Apps Script did not return valid JSON: "
                + response.text[:500]
            )

        if not result.get("success"):
            raise RuntimeError(
                "Google Apps Script rejected the request: "
                + str(result.get("error", "Unknown error"))
            )

        print(
            "GOOGLE APPS SCRIPT HTML PAYMENT REQUEST SENT:",
            reservation
        )

        return result

    except Exception as error:
        print("GOOGLE APPS SCRIPT ERROR:", repr(error))
        raise RuntimeError(
            f"GOOGLE APPS SCRIPT ERROR: {error!r}"
        )


@app.route("/update-customer/<number>", methods=["POST"])
def update_customer(number):
    conn = psycopg2.connect(DATABASE_URL)

    try:
        client_name = (request.form.get("client_name") or "").strip()
        client_phone = (request.form.get("client_phone") or "").strip()
        client_email = (request.form.get("client_email") or "").strip()

        if not client_name or not client_phone or not client_email:
            return jsonify({
                "success": False,
                "error": "Name, phone number and email are required."
            }), 400

        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM reservations WHERE reservation_number = %s",
                (number,)
            )
            reservation = cur.fetchone()

            if not reservation:
                return jsonify({
                    "success": False,
                    "error": "Reservation not found."
                }), 404

            cur.execute(
                """
                UPDATE reservations
                SET client_name = %s,
                    client_phone = %s,
                    client_email = %s
                WHERE reservation_number = %s
                """,
                (client_name, client_phone, client_email, number)
            )

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Customer details saved successfully.",
            "reservation_number": number
        })

    except Exception as error:
        conn.rollback()
        print("UPDATE CUSTOMER ERROR:", repr(error))

        return jsonify({
            "success": False,
            "error": "Could not save customer details."
        }), 500

    finally:
        conn.close()

@app.route("/request-payment-details/<number>", methods=["POST"])
def request_payment_details(number):

    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM reservations WHERE reservation_number = %s",
                (number,)
            )
            row = cur.fetchone()

    finally:
        conn.close()

    if not row:
        return jsonify({
            "success": False,
            "error": "Reservation not found"
        }), 404

    data = dict(row)

    customer_email = (
        data.get("client_email") or ""
    ).strip()

    customer_name = (
        data.get("client_name") or ""
    ).strip()

    customer_phone = (
        data.get("client_phone") or ""
    ).strip()

    if not customer_name or not customer_phone or not customer_email:
        return jsonify({
            "success": False,
            "error": (
                "Please enter your name, phone number "
                "and email before requesting payment details."
            )
        }), 400

    try:
        check_in_date = datetime.strptime(
            data["check_in"], "%Y-%m-%d"
        ).date()

        check_out_date = datetime.strptime(
            data["check_out"], "%Y-%m-%d"
        ).date()

        data["nights"] = (
            check_out_date - check_in_date
        ).days

    except (ValueError, TypeError):
        data["nights"] = 0

    try:
        send_payment_request_email(data)

        return jsonify({
            "success": True,
            "message": (
                "Your payment-details request has been "
                "sent successfully."
            ),
            "reservation_number": number
        })

    except Exception as error:
        print(
            "PAYMENT REQUEST EMAIL ERROR:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "error": repr(error)
        }), 500


@app.route("/reservation-data/<number>")
def reservation_data(number):
    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM reservations WHERE reservation_number = %s",
                (number,)
            )
            row = cur.fetchone()

    finally:
        conn.close()

    if not row:
        return jsonify({"error": "Reservation not found"}), 404

    data = dict(row)

    try:
        check_in_date = datetime.strptime(
            data["check_in"], "%Y-%m-%d"
        ).date()

        check_out_date = datetime.strptime(
            data["check_out"], "%Y-%m-%d"
        ).date()

        data["nights"] = (
            check_out_date - check_in_date
        ).days

    except (ValueError, TypeError):
        data["nights"] = 0

    return jsonify(data)

@app.route("/admin/reservations")
def reservations():
    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM reservations
                ORDER BY id DESC
            """)
            rows = cur.fetchall()

    finally:
        conn.close()

    return jsonify(rows)

@app.route("/images/<path:filename>")
def images(filename):
    return send_from_directory(BASE / "images", filename)


@app.route("/db-test")
def db_test():
    try:
        conn = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor
        )

        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS count FROM reservations"
            )
            row = cur.fetchone()

        conn.close()

        return jsonify({
            "success": True,
            "database": "PostgreSQL",
            "reservations_count": row["count"]
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "error": repr(error)
        }), 500



@app.route("/admin/migrate-reservations", methods=["POST"])
def migrate_reservations():
    supplied_secret = request.headers.get("X-Migration-Secret", "")
    expected_secret = os.environ.get("MIGRATION_SECRET", "")

    if not expected_secret or supplied_secret != expected_secret:
        return jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401

    data = request.get_json(silent=True)

    if not isinstance(data, list):
        return jsonify({
            "success": False,
            "error": "Expected a JSON array"
        }), 400

    conn = None

    try:
        conn = psycopg2.connect(DATABASE_URL)

        inserted = 0
        skipped = 0

        with conn.cursor() as cur:
            for item in data:
                cur.execute("""
                    INSERT INTO reservations
                    (
                        reservation_number,
                        region,
                        check_in,
                        check_out,
                        adults,
                        children,
                        accommodation,
                        price,
                        created_at,
                        client_name,
                        client_phone,
                        client_email
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (reservation_number) DO NOTHING
                """, (
                    item.get("reservation_number"),
                    item.get("region"),
                    item.get("check_in"),
                    item.get("check_out"),
                    item.get("adults"),
                    item.get("children"),
                    item.get("accommodation"),
                    item.get("price"),
                    item.get("created_at"),
                    item.get("client_name"),
                    item.get("client_phone"),
                    item.get("client_email")
                ))

                if cur.rowcount == 1:
                    inserted += 1
                else:
                    skipped += 1

        conn.commit()

        return jsonify({
            "success": True,
            "received": len(data),
            "inserted": inserted,
            "skipped_existing": skipped
        })

    except Exception as error:
        if conn:
            conn.rollback()

        return jsonify({
            "success": False,
            "error": repr(error)
        }), 500

    finally:
        if conn:
            conn.close()


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

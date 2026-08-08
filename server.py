from flask import Flask, request, redirect, send_from_directory, jsonify
from flask_cors import CORS
import sqlite3
from pathlib import Path
from datetime import datetime
import secrets

app = Flask(__name__)
CORS(app, origins=["https://albertoo404.github.io"])

BASE = Path(__file__).resolve().parent
DB = BASE / "reservations.db"
RECEIPTS = BASE / "reservations"
RECEIPTS.mkdir(exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_number TEXT UNIQUE NOT NULL,
            region TEXT NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            adults INTEGER NOT NULL,
            children INTEGER NOT NULL,
            accommodation TEXT NOT NULL,
            price REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
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
    <img src="/images/exumalogo.jpg"
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
    <span class="label">Price</span>
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

@app.route("/reserve", methods=["POST"])
def reserve():
    region = request.form.get("region", "").strip()
    check_in = request.form.get("check_in", "").strip()
    check_out = request.form.get("check_out", "").strip()
    accommodation = request.form.get("accommodation", "").strip()

    try:
        adults = max(1, int(request.form.get("adults", "1")))
        children = max(0, int(request.form.get("children", "0")))
        price = float(request.form.get("price", "0"))
    except ValueError:
        return "Invalid reservation information", 400

    if not region or not check_in or not check_out or not accommodation:
        return "Missing reservation information", 400

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
        "created_at": created_at
    }

    conn = sqlite3.connect(DB)
    conn.execute("""
        INSERT INTO reservations
        (reservation_number, region, check_in, check_out,
         adults, children, accommodation, price, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        number,
        region,
        check_in,
        check_out,
        adults,
        children,
        accommodation,
        price,
        created_at
    ))
    conn.commit()
    conn.close()

    create_receipt(data)

    # Silent transition to the generated receipt
    return redirect(f"/reservation/{number}")

@app.route("/reservation/<number>")
def receipt(number):
    filename = f"{number}.html"

    if not (RECEIPTS / filename).exists():
        return "Reservation not found", 404

    return send_from_directory(RECEIPTS, filename)

@app.route("/admin/reservations")
def reservations():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT * FROM reservations
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify([dict(row) for row in rows])

@app.route("/images/<path:filename>")
def images(filename):
    return send_from_directory(BASE / "images", filename)

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

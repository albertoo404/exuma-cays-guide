            "reservations_count": count
        })

    except Exception:
        app.logger.exception("Health check failed")
        return jsonify({
            "success": False,
            "database": "unavailable"
        }), 503

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
                if not row:        return jsonify({"success": False, "error": "Migration failed."}), 500
    finally:
        if conn:
            conn.close()


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
        return jsonify({"success": False, "error": "Please provide your name, email address and phone number."}), 400
    if len(name) > 120 or len(email) > 254 or len(phone) > 60:
        return jsonify({"success": False, "error": "One or more contact fields are too long."}), 400
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        return jsonify({"success": False, "error": "Please enter a valid email address."}), 400

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
    safe = lambda value: html.escape(str(value if value is not None else ""))
    rows = "".join(
        f'<tr><th align="left" style="padding:10px;border-bottom:1px solid #e5ecef">{safe(key)}</th>'
        f'<td style="padding:10px;border-bottom:1px solid #e5ecef;white-space:pre-wrap">{safe(value)}</td></tr>'
        for key, value in fields.items()
    )
    plain = "New boat rental enquiry\n\n" + "\n".join(f"{key}: {value}" for key, value in fields.items())
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
            "subject": f"New Boat Rental Enquiry — {fields['Customer name']}",
            "message": plain,
            "htmlBody": body_html,
            "enquiry": fields,
        })
        return jsonify({"success": True, "message": "Your boat rental enquiry has been sent. We will contact you soon."}), 200
    except Exception:
        app.logger.exception("Boat enquiry email failed")
        return jsonify({"success": False, "error": "We could not send your enquiry right now. Please try again later or contact the business by email."}), 502


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


# Initialise tables when the service starts. If the database is temporarily down,
# let Gunicorn start so /health can report the failure and Render logs show details.
try:
    init_db()
except Exception:
    app.logger.exception("Database initialization failed during startup")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)

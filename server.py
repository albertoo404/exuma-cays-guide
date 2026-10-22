                    INSERT INTO reservations
                    (reservation_number, region, check_in, check_out, adults, children,
                     accommodation, price, created_at, client_name, client_phone, client_email)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (reservation_number) DO NOTHING
                """, (item.get("reservation_number"), item.get("region"), item.get("check_in"),
                      item.get("check_out"), item.get("adults"), item.get("children"),
                      item.get("accommodation"), item.get("price"), item.get("created_at"),
                      item.get("client_name"), item.get("client_phone"), item.get("client_email")))
                if cur.rowcount == 1:
                    inserted += 1
                else:
                    skipped += 1
        conn.commit()
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
    """
    Send a boat-rental enquiry to the business email through Google Apps Script.
    Does not write to or alter the accommodation reservations database.
    """
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

    # Limit input lengths and strip control characters to avoid oversized/spoofed emails.
    fields = {
        "Customer name": name[:120],
        "Customer email": email[:254],
        "Phone": phone[:60],
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
        result = google_apps_script_send({
            "action": "payment_request",  # Reuse the existing Apps Script email action for compatibility
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
        return jsonify({
            "success": False,
            "error": "We could not send your enquiry right now. Please try again later or contact the business by email."
        }), 502


init_db()

if __name__ == "__main__":
    # Use debug=False in production (Render).
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)

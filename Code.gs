const SHEET_NAME = "Reservations";
const COMPANY_EMAIL = "exumaaccomodations@gmail.com";

function doGet(e) {
  return jsonResponse({
    success: true,
    service: "Exuma Cays Reservation System",
    status: "online"
  });
}

function doPost(e) {
  try {

    if (!e || !e.postData || !e.postData.contents) {
      return jsonResponse({
        success: false,
        error: "Empty request"
      });
    }

    const data = JSON.parse(e.postData.contents);

    /*
     * PAYMENT DETAILS REQUEST
     */
    if (data.action === "payment_request") {

      if (!data.to || !data.subject || !data.htmlBody) {
        return jsonResponse({
          success: false,
          error: "Payment request requires to, subject and htmlBody."
        });
      }

      MailApp.sendEmail(
        data.to,
        data.subject,
        data.message || "Payment details request.",
        {
          htmlBody: data.htmlBody
        }
      );

      return jsonResponse({
        success: true,
        type: "payment_request",
        message: "HTML payment request email sent successfully."
      });
    }


    /*
     * NORMAL RESERVATION REQUEST
     */

    const required = [
      "customerName",
      "customerEmail",
      "customerPhone",
      "accommodation",
      "checkIn",
      "checkOut",
      "guests"
    ];

    for (let i = 0; i < required.length; i++) {

      const field = required[i];

      if (
        data[field] === undefined ||
        data[field] === null ||
        String(data[field]).trim() === ""
      ) {

        return jsonResponse({
          success: false,
          error: "Missing field: " + field
        });

      }
    }


    const reservationId = createReservationId();

    const sheet = getReservationsSheet();

    sheet.appendRow([
      new Date(),
      reservationId,
      String(data.customerName),
      String(data.customerEmail),
      String(data.customerPhone),
      String(data.accommodation),
      String(data.checkIn),
      String(data.checkOut),
      String(data.guests),
      String(data.message || ""),
      "PENDING"
    ]);


    sendCompanyNotification(
      data,
      reservationId
    );


    return jsonResponse({
      success: true,
      reservationId: reservationId,
      status: "PENDING",
      message: "Reservation request received successfully."
    });


  } catch (error) {

    console.error(error);

    return jsonResponse({
      success: false,
      error: String(
        error && error.message
          ? error.message
          : error
      ),
      stack: String(
        error && error.stack
          ? error.stack
          : ""
      )
    });

  }
}


function getReservationsSheet() {

  const properties =
    PropertiesService.getScriptProperties();

  let spreadsheetId =
    properties.getProperty(
      "RESERVATION_SHEET_ID"
    );

  let spreadsheet;


  if (spreadsheetId) {

    try {

      spreadsheet =
        SpreadsheetApp.openById(
          spreadsheetId
        );

    } catch (error) {

      spreadsheet = null;

    }

  }


  if (!spreadsheet) {

    spreadsheet =
      SpreadsheetApp.create(
        "Exuma Cays Reservation Requests"
      );

    properties.setProperty(
      "RESERVATION_SHEET_ID",
      spreadsheet.getId()
    );

  }


  let sheet =
    spreadsheet.getSheetByName(
      SHEET_NAME
    );


  if (!sheet) {

    sheet =
      spreadsheet.insertSheet(
        SHEET_NAME
      );

  }


  if (sheet.getLastRow() === 0) {

    sheet.appendRow([
      "Timestamp",
      "Reservation ID",
      "Customer Name",
      "Customer Email",
      "Customer Phone",
      "Accommodation",
      "Check In",
      "Check Out",
      "Guests",
      "Message",
      "Status"
    ]);

    sheet.setFrozenRows(1);

  }


  return sheet;
}


function sendCompanyNotification(
  data,
  reservationId
) {

  const subject =
    "New Exuma Cays Reservation Request - " +
    reservationId;


  const htmlBody = `

<!DOCTYPE html>

<html>

<body style="
margin:0;
padding:25px 10px;
background:#f4f7f9;
font-family:Arial,sans-serif;
color:#173b43;
">

<div style="
max-width:650px;
margin:auto;
background:#ffffff;
border-radius:16px;
overflow:hidden;
">

<div style="
background:#087f8c;
padding:28px;
text-align:center;
color:white;
">

<h1 style="
margin:0;
font-size:28px;
">
EXUMA CAYS
</h1>

<p style="
margin:8px 0 0;
font-size:15px;
">
New Reservation Request
</p>

</div>


<div style="
padding:30px;
">

<div style="
background:#eef9fa;
border-left:5px solid #087f8c;
padding:18px;
margin-bottom:25px;
">

<strong>Reservation ID</strong>

<br>

<span style="
font-size:20px;
color:#087f8c;
">

${escapeHtml(reservationId)}

</span>

</div>


<h2>Customer Details</h2>


<table style="
width:100%;
border-collapse:collapse;
">

<tr>

<td style="
padding:10px;
font-weight:bold;
">
Name
</td>

<td style="
padding:10px;
">
${escapeHtml(data.customerName)}
</td>

</tr>


<tr>

<td style="
padding:10px;
font-weight:bold;
">
Email
</td>

<td style="
padding:10px;
">
${escapeHtml(data.customerEmail)}
</td>

</tr>


<tr>

<td style="
padding:10px;
font-weight:bold;
">
Phone
</td>

<td style="
padding:10px;
">
${escapeHtml(data.customerPhone)}
</td>

</tr>

</table>


<h2>Accommodation Details</h2>


<table style="
width:100%;
border-collapse:collapse;
">

<tr>

<td style="
padding:10px;
font-weight:bold;
">
Accommodation
</td>

<td style="
padding:10px;
">
${escapeHtml(data.accommodation)}
</td>

</tr>


<tr>

<td style="
padding:10px;
font-weight:bold;
">
Check-in
</td>

<td style="
padding:10px;
">
${escapeHtml(data.checkIn)}
</td>

</tr>


<tr>

<td style="
padding:10px;
font-weight:bold;
">
Check-out
</td>

<td style="
padding:10px;
">
${escapeHtml(data.checkOut)}
</td>

</tr>


<tr>

<td style="
padding:10px;
font-weight:bold;
">
Guests
</td>

<td style="
padding:10px;
">
${escapeHtml(data.guests)}
</td>

</tr>

</table>


<h2>Customer Message</h2>


<div style="
background:#f7f7f7;
padding:18px;
border-radius:8px;
">

${escapeHtml(
  data.message ||
  "No additional message"
)}

</div>


<div style="
background:#fff4d6;
padding:18px;
border-radius:8px;
margin-top:25px;
">

<strong>Status:</strong>

<span style="
color:#b26a00;
">

PENDING

</span>

<br>

Awaiting accommodation confirmation.

</div>


</div>


<div style="
background:#f1f1f1;
padding:20px;
text-align:center;
color:#777;
font-size:12px;
">

Exuma Cays Reservation System

<br>

This is an automated reservation notification.

</div>


</div>

</body>

</html>

`;


  const plainTextBody =

"NEW RESERVATION REQUEST\n\n" +

"Reservation ID: " +
reservationId +
"\n\n" +

"CUSTOMER DETAILS\n" +

"Name: " +
data.customerName +
"\n" +

"Email: " +
data.customerEmail +
"\n" +

"Phone: " +
data.customerPhone +
"\n\n" +

"ACCOMMODATION\n" +

"Accommodation: " +
data.accommodation +
"\n" +

"Check-in: " +
data.checkIn +
"\n" +

"Check-out: " +
data.checkOut +
"\n" +

"Guests: " +
data.guests +
"\n\n" +

"CUSTOMER MESSAGE\n" +

(data.message ||
"No additional message") +

"\n\nSTATUS\nPENDING";


  MailApp.sendEmail(
    COMPANY_EMAIL,
    subject,
    plainTextBody,
    {
      htmlBody: htmlBody
    }
  );

}


function escapeHtml(value) {

  return String(value || "")

    .replace(/&/g, "&amp;")

    .replace(/</g, "&lt;")

    .replace(/>/g, "&gt;")

    .replace(/"/g, "&quot;")

    .replace(/'/g, "&#039;");

}


function createReservationId() {

  const timestamp =
    new Date()
      .getTime()
      .toString()
      .slice(-8);


  const random =
    Math.floor(
      1000 +
      Math.random() *
      9000
    );


  return (
    "EXM-" +
    timestamp +
    "-" +
    random
  );

}


function jsonResponse(data) {

  return ContentService
    .createTextOutput(
      JSON.stringify(data)
    )
    .setMimeType(
      ContentService.MimeType.JSON
    );

}


function authorizeReservationSystem() {

  const ss =
    SpreadsheetApp.create(
      "Exuma Cays Authorization Test"
    );

  const sheet =
    ss.getActiveSheet();

  sheet
    .getRange("A1")
    .setValue(
      "Authorization successful"
    );


  MailApp.sendEmail(
    COMPANY_EMAIL,
    "Exuma Cays Authorization Test",
    "Google Sheets and Mail permissions are authorized."
  );


  Logger.log(
    "Authorization successful."
  );

  Logger.log(
    "Spreadsheet: " +
    ss.getUrl()
  );

}

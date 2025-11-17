import os
import smtplib
from email.message import EmailMessage
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr

from database import db, create_document

app = FastAPI(title="Jain Foam & Furnishing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ContactSubmission(BaseModel):
    name: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=6, max_length=20)
    email: Optional[EmailStr] = None
    message: str = Field(..., min_length=5, max_length=1000)


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def read_root():
    return {"message": "Jain Foam & Furnishing Backend Running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


def send_email_notification(submission: ContactSubmission):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    to_email = os.getenv("SMTP_TO", "raiv5253@gmail.com")
    from_email = os.getenv("SMTP_FROM", smtp_user or "no-reply@jain-foam.local")

    if not smtp_host or not smtp_user or not smtp_pass:
        # If SMTP not configured, skip sending but not an error
        return False

    msg = EmailMessage()
    msg["Subject"] = f"New Enquiry from {submission.name}"
    msg["From"] = from_email
    msg["To"] = to_email

    body = (
        f"New enquiry received from website\n\n"
        f"Name: {submission.name}\n"
        f"Phone: {submission.phone}\n"
        f"Email: {submission.email or '-'}\n\n"
        f"Message:\n{submission.message}\n"
    )
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception:
        return False


@app.post("/api/contact")
def submit_contact(submission: ContactSubmission):
    try:
        # Store in database for persistence
        if db is None:
            raise Exception("Database not configured")
        create_document("contactsubmission", submission)
    except Exception as e:
        # Not fatal for user; we still try to email
        pass

    email_sent = send_email_notification(submission)

    return {
        "ok": True,
        "message": "Thank you! Your enquiry has been received. We'll reach out shortly.",
        "email_sent": email_sent,
    }


@app.post("/api/chatbot")
def chatbot(req: ChatRequest):
    user = req.message.lower().strip()

    def reply(text: str):
        return {"reply": text}

    if any(k in user for k in ["time", "timing", "open", "closing", "hours"]):
        return reply("We are open every day from 10:00 AM to 10:00 PM. Same-day delivery is available.")

    if any(k in user for k in ["address", "location", "where", "map", "reach"]):
        return reply("Shop No. 8-9, Panch Bhagini Sadan, BP Road, Opp. Vijay Punjab Hotel, Bhayandar East, Thane, Mira Bhayandar, Maharashtra 401105. Search 'Jain Foam & Furnishing' on Google Maps for directions.")

    if any(k in user for k in ["deliver", "delivery", "same day", "home delivery"]):
        return reply("Yes, we offer same-day delivery across Bhayandar, Mira Road, and Dahisar.")

    if any(k in user for k in ["price", "cost", "rate", "charges"]):
        return reply("Prices vary by product and customization. Share what you need (mattress size, curtain fabric, sofa design) and we’ll give you the best quote.")

    if any(k in user for k in ["mattress", "curtain", "sofa", "wallpaper", "carpet", "blinds", "pillow", "cushion", "grass", "floor", "rug"]):
        return reply("We stock premium mattresses, curtains, wallpapers, carpets, PVC flooring, window blinds, sofa making & repair, pillows, cushions and more. Tell me what you’re looking for.")

    if any(k in user for k in ["contact", "phone", "call", "whatsapp"]):
        return reply("You can call us at 083690 51217 or email raiv5253@gmail.com. We’re happy to help!")

    if any(k in user for k in ["instagram", "photo", "gallery"]):
        return reply("Check our latest updates and photos on Instagram: @jain_foam — https://www.instagram.com/jain_foam?igsh=bDZhanJrNHJ0NXdv")

    if any(k in user for k in ["hello", "hi", "hey"]):
        return reply("Hi! I’m your assistant for Jain Foam & Furnishing. Ask me about products, timings, delivery, or pricing.")

    return reply("I didn’t catch that. Ask me about products, prices, timings, delivery, or our location.")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

"""Transactional email via Resend. Used for magic link auth (Month 2) and notifications."""
import os
import resend
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.environ["RESEND_API_KEY"]

FROM_ADDRESS = os.environ["EMAIL_FROM"]  # e.g. "TTFL Tracker <noreply@yourdomain.com>"


def send_email(*, to: str, subject: str, html: str) -> str:
    """Send a transactional email. Returns the Resend message ID."""
    response = resend.Emails.send({
        "from": FROM_ADDRESS,
        "to": to,
        "subject": subject,
        "html": html,
    })
    return response["id"]


def send_magic_link(*, to: str, link: str) -> str:
    """Send a magic link login email."""
    html = f"""
    <p>Click the link below to sign in to TTFL Tracker. It expires in 15 minutes.</p>
    <p><a href="{link}">Sign in</a></p>
    <p>If you didn't request this, you can safely ignore this email.</p>
    """
    return send_email(to=to, subject="Your TTFL Tracker sign-in link", html=html)

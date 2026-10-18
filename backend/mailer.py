"""Email alerts for new project requests (works with Gmail App Passwords)."""
import logging
import smtplib
import ssl
import threading
from email.message import EmailMessage
from email.utils import formataddr

log = logging.getLogger("rh_labs.mail")


def enabled(cfg) -> bool:
    return bool(cfg.SMTP_HOST and cfg.SMTP_USER and cfg.SMTP_PASSWORD and cfg.NOTIFY_EMAIL)


def _one_line(value: str) -> str:
    return " ".join(str(value).split())[:120]


def _deliver(cfg, msg: EmailMessage) -> None:
    try:
        context = ssl.create_default_context()
        if cfg.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(cfg.SMTP_HOST, cfg.SMTP_PORT, context=context, timeout=20) as smtp:
                smtp.login(cfg.SMTP_USER, cfg.SMTP_PASSWORD)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(cfg.SMTP_HOST, cfg.SMTP_PORT, timeout=20) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                smtp.login(cfg.SMTP_USER, cfg.SMTP_PASSWORD)
                smtp.send_message(msg)
        log.info("Email sent: %s", msg["Subject"])
    except Exception:  # never crash a request because email failed
        log.exception("Email failed: %s", msg["Subject"])


def _send_async(cfg, msg: EmailMessage) -> None:
    threading.Thread(target=_deliver, args=(cfg, msg), daemon=True).start()


def build_lead_email(cfg, lead: dict, lead_id) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"New project request: {_one_line(lead['service'])} from {_one_line(lead['name'])}"
    msg["From"] = formataddr((f"{cfg.COMPANY_NAME} Website", cfg.SMTP_USER))
    msg["To"] = cfg.NOTIFY_EMAIL
    msg["Reply-To"] = lead["email"]
    msg.set_content(
        f"New project request #{lead_id if lead_id is not None else '-'}\n\n"
        f"Name:     {lead['name']}\n"
        f"Email:    {lead['email']}\n"
        f"Company:  {lead.get('company') or '-'}\n"
        f"Service:  {lead['service']}\n"
        f"Budget:   {lead.get('budget') or '-'}\n"
        f"Deadline: {lead.get('deadline') or '-'}\n\n"
        f"Project details:\n{lead['details']}\n\n"
        "Reply to this email to answer the client directly.\n"
    )
    return msg


def notify_new_lead(cfg, lead: dict, lead_id) -> bool:
    """Send the alert in the background. Returns True if an email was queued."""
    if not enabled(cfg):
        return False
    _send_async(cfg, build_lead_email(cfg, lead, lead_id))
    return True


def send_auto_reply(cfg, lead: dict) -> bool:
    if not (enabled(cfg) and cfg.SEND_AUTO_REPLY):
        return False
    first = _one_line(lead["name"]).split(" ")[0]
    msg = EmailMessage()
    msg["Subject"] = f"We received your project request - {cfg.COMPANY_NAME}"
    msg["From"] = formataddr((cfg.COMPANY_NAME, cfg.SMTP_USER))
    msg["To"] = lead["email"]
    msg["Reply-To"] = cfg.NOTIFY_EMAIL
    msg.set_content(
        f"Hi {first},\n\n"
        f"Thank you for contacting {cfg.COMPANY_NAME}. We received your request for: {lead['service']}.\n"
        "Our team will reply within one working day with questions or a quote.\n\n"
        f"Best regards,\n{cfg.COMPANY_NAME}\n"
    )
    _send_async(cfg, msg)
    return True

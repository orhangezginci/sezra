import email
import imaplib
import json
import re
import os
import time
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from uuid import uuid4

import pika
import html2text

COMPONENT_METADATA_PATH = Path("/app/component.json")


def load_component_metadata() -> dict:
    with open(COMPONENT_METADATA_PATH, "r") as file:
        return json.load(file)


component_metadata = load_component_metadata()
config = component_metadata["config"]
rabbitmq_config = component_metadata["rabbitmq"]

IMAP_HOST = config["imap_host"]
IMAP_PORT = config["imap_port"]
POLL_INTERVAL_SECONDS = config["poll_interval_seconds"]
SUBJECT_KEYWORD = config["subject_keyword"]

RAW_EXCHANGE = rabbitmq_config["exchange"]


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


GMAIL_EMAIL = required_env("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = required_env("GMAIL_APP_PASSWORD")

RABBITMQ_HOST = required_env("RABBITMQ_HOST")
RABBITMQ_PORT = int(required_env("RABBITMQ_PORT"))
RABBITMQ_USER = required_env("RABBITMQ_USER")
RABBITMQ_PASSWORD = required_env("RABBITMQ_PASSWORD")


# ====================== HTML2TEXT SETUP ======================
h = html2text.HTML2Text()
h.ignore_links = True
h.ignore_images = True
h.ignore_emphasis = True
h.ignore_tables = False      # Change to True if you prefer simple tables
h.body_width = 0             # No line wrapping
h.single_line_break = True
h.unicode_snob = True


def html_to_plain_text(html_content: str) -> str:
    """Convert HTML to clean plain text using html2text."""
    if not html_content or not html_content.strip():
        return ""
    
    try:
        text = h.handle(html_content)
        # Clean up whitespace
        lines = [
            line.strip() 
            for line in text.splitlines() 
            if line.strip()
        ]
        return "\n".join(lines)
    except Exception:
        return html_content.strip()


def extract_email_body(message: Message) -> str:
    """Extract the best possible plain text body from an email message."""
    if not message:
        return ""

    # Preferred method: Let email library choose best part (plain > html)
    try:
        body_part = message.get_body(preferencelist=('plain', 'html'))
        if body_part:
            payload = body_part.get_payload(decode=True)
            if payload:
                charset = body_part.get_content_charset('utf-8')
                content = payload.decode(charset, errors="replace")
                
                if body_part.get_content_type() == "text/plain":
                    return content.strip()
                else:
                    return html_to_plain_text(content)
    except Exception:
        pass  # Fall back to manual parsing

    # Fallback: Manual walk through multipart
    if message.is_multipart():
        html_body = None
        
        for part in message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", "")).lower()

            if "attachment" in content_disposition:
                continue

            payload = part.get_payload(decode=True)
            if not payload:
                continue

            charset = part.get_content_charset('utf-8')
            text = payload.decode(charset, errors="replace")

            if content_type == "text/plain":
                return text.strip()  # Prefer plain text

            if content_type == "text/html":
                html_body = text

        if html_body:
            return html_to_plain_text(html_body)
        
        return ""

    # Single part email
    payload = message.get_payload(decode=True)
    if payload:
        charset = message.get_content_charset('utf-8')
        text = payload.decode(charset, errors="replace")
        
        if message.get_content_type() == "text/html":
            return html_to_plain_text(text)
        return text.strip()

    return ""


def transform_email_to_sezra_event(message: Message, body: str) -> dict:
    event_id = str(uuid4())

    return {
        "event_id": event_id,
        "event_type": "GmailMessageReceived",
        "source": component_metadata["service_name"],
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": None,
        "causation_id": None,
        "payload": {
            "from": message.get("From"),
            "subject": message.get("Subject"),
            "date": message.get("Date"),
            "text": body,
        },
    }


def publish_event(channel, event: dict) -> None:
    channel.basic_publish(
        exchange=RAW_EXCHANGE,
        routing_key="",
        body=json.dumps(event).encode("utf-8"),
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,
        ),
    )


def process_unseen_emails(mailbox: imaplib.IMAP4_SSL, channel) -> None:
    status, data = mailbox.search(
        None,
        "UNSEEN",
        "SUBJECT",
        f'"{SUBJECT_KEYWORD}"',
    )

    if status != "OK":
        print("Could not search Gmail inbox")
        return

    email_ids = data[0].split()

    for email_id in email_ids:
        status, message_data = mailbox.fetch(email_id, "(RFC822)")

        if status != "OK":
            print(f"Could not fetch email: {email_id.decode()}")
            continue

        raw_email = message_data[0][1]
        message = email.message_from_bytes(raw_email)

        body = extract_email_body(message)

        sezra_event = transform_email_to_sezra_event(message, body)
        publish_event(channel, sezra_event)

        mailbox.store(email_id, "+FLAGS", "\\Seen")

        print(
            f"Published Gmail event: "
            f"{sezra_event['event_id']} "
            f"subject={message.get('Subject')}"
        )


def connect_to_rabbitmq() -> pika.BlockingConnection:
    credentials = pika.PlainCredentials(
        username=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD,
    )

    while True:
        try:
            return pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    credentials=credentials,
                    heartbeat=30,
                    blocked_connection_timeout=300,
                )
            )
        except pika.exceptions.AMQPConnectionError:
            print("RabbitMQ not ready yet. Retrying...")
            time.sleep(3)


def connect_to_gmail() -> imaplib.IMAP4_SSL:
    mailbox = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mailbox.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
    mailbox.select("INBOX")
    return mailbox


def main() -> None:
    print(
        f"Starting component: "
        f"{component_metadata['display_name']} "
        f"({component_metadata['id']})"
    )

    print(f"Publishing Gmail events to exchange: {RAW_EXCHANGE}")

    while True:
        rabbitmq_connection = None

        try:
            rabbitmq_connection = connect_to_rabbitmq()
            channel = rabbitmq_connection.channel()

            channel.exchange_declare(
                exchange=RAW_EXCHANGE,
                exchange_type="fanout",
                durable=True,
            )

            mailbox = connect_to_gmail()
            process_unseen_emails(mailbox, channel)
            mailbox.logout()

        except Exception as error:
            print(f"Gmail polling failed: {error}")

        finally:
            if rabbitmq_connection and rabbitmq_connection.is_open:
                rabbitmq_connection.close()

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
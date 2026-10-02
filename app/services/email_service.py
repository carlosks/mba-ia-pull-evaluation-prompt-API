"""
Envio de e-mails por SMTP.

Funciona com qualquer provedor SMTP (Gmail com senha de app, Brevo,
Resend, Amazon SES...). Sem SMTP_HOST configurado, nada é enviado e o
evento fica registrado no log.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app import config

logger = logging.getLogger("app.email")

# Substituível nos testes: recebe a EmailMessage pronta.
sender = None


def _deliver_smtp(message: EmailMessage) -> None:
    context = ssl.create_default_context()

    if config.SMTP_USE_SSL:
        server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=20, context=context)
    else:
        server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20)

    with server:
        if not config.SMTP_USE_SSL:
            server.starttls(context=context)

        if config.SMTP_USERNAME:
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)

        server.send_message(message)


def send_email(to: str, subject: str, text_body: str, html_body: str | None = None) -> bool:
    """Envia um e-mail. Retorna True se foi entregue ao servidor SMTP."""
    if not config.email_enabled():
        logger.warning("E-mail não configurado (SMTP_HOST); mensagem para %s não enviada.", to)
        return False

    message = EmailMessage()
    message["From"] = formataddr((config.EMAIL_FROM_NAME, config.EMAIL_FROM))
    message["To"] = to
    message["Subject"] = subject
    message["Message-ID"] = make_msgid(domain=config.EMAIL_FROM.split("@")[-1])
    message.set_content(text_body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        (sender or _deliver_smtp)(message)
        logger.info("E-mail '%s' enviado para %s", subject, to)
        return True
    except Exception:
        logger.exception("Falha ao enviar e-mail '%s' para %s", subject, to)
        return False

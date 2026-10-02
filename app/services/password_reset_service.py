"""
Recuperação de senha ("esqueci minha senha").

- O link enviado por e-mail carrega um token aleatório; no banco fica só
  o hash SHA-256 dele, para que um vazamento do banco não permita trocar
  senhas.
- O link vale PASSWORD_RESET_EXPIRE_MINUTES e só pode ser usado uma vez.
- Trocar a senha invalida os outros links pendentes e encerra as sessões
  abertas (ver users.password_changed_at em app.security).
- A resposta ao pedido é sempre a mesma, exista ou não o e-mail, para não
  revelar quem tem conta.
"""

from __future__ import annotations

import hashlib
import html
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import config, models
from app.services import email_service

logger = logging.getLogger("app.password_reset")

REQUEST_MESSAGE = (
    "Se houver uma conta com esse e-mail, enviamos um link para criar uma nova senha. "
    "Confira a caixa de entrada e o spam."
)
INVALID_LINK_MESSAGE = "Este link é inválido ou expirou. Peça um novo em \"Esqueci minha senha\"."


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def reset_link(token: str) -> str:
    # O token vai depois do "#": o navegador não o envia ao servidor nem o
    # grava nos logs de acesso.
    return f"{config.PUBLIC_BASE_URL}/static/nova-senha.html#token={token}"


def create_reset_token(db: Session, user: models.User) -> str | None:
    """Gera um token para o usuário, respeitando o limite por hora."""
    since = _now() - timedelta(hours=1)
    recent = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.user_id == user.id,
            models.PasswordResetToken.created_at >= since,
        )
        .count()
    )

    if recent >= config.PASSWORD_RESET_MAX_PER_HOUR:
        logger.warning("Limite de pedidos de recuperação atingido para o usuário %s", user.id)
        return None

    token = secrets.token_urlsafe(32)
    db.add(
        models.PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(token),
            expires_at=_now() + timedelta(minutes=config.PASSWORD_RESET_EXPIRE_MINUTES),
            created_at=_now(),
        )
    )
    db.commit()
    return token


def build_email(token: str) -> tuple[str, str, str]:
    link = reset_link(token)
    minutes = config.PASSWORD_RESET_EXPIRE_MINUTES
    subject = "Crie uma nova senha - MBA IA"

    text_body = (
        "Olá,\n\n"
        "Recebemos um pedido para criar uma nova senha na sua conta do MBA IA - Bug Evaluation.\n\n"
        f"Para continuar, abra o link abaixo (vale por {minutes} minutos e só pode ser usado uma vez):\n\n"
        f"{link}\n\n"
        "Se não foi você, ignore este e-mail: sua senha atual continua valendo.\n"
    )

    safe_link = html.escape(link, quote=True)
    html_body = f"""\
<!DOCTYPE html>
<html lang="pt-BR">
  <body style="margin:0;padding:24px;background:#f3f6fb;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
      <tr><td align="center">
        <table role="presentation" width="100%" style="max-width:520px;background:#ffffff;border-radius:16px;padding:32px;" cellspacing="0" cellpadding="0">
          <tr><td>
            <h1 style="margin:0 0 16px;font-size:22px;">Crie uma nova senha</h1>
            <p style="margin:0 0 16px;line-height:1.5;">
              Recebemos um pedido para criar uma nova senha na sua conta do <strong>MBA IA - Bug Evaluation</strong>.
            </p>
            <p style="margin:24px 0;">
              <a href="{safe_link}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;font-weight:bold;padding:14px 24px;border-radius:10px;">Criar nova senha</a>
            </p>
            <p style="margin:0 0 16px;line-height:1.5;color:#475569;font-size:14px;">
              O link vale por {minutes} minutos e só pode ser usado uma vez.
              Se o botão não funcionar, copie e cole este endereço no navegador:<br />
              <span style="word-break:break-all;color:#2563eb;">{safe_link}</span>
            </p>
            <p style="margin:0;line-height:1.5;color:#475569;font-size:14px;">
              Se não foi você, ignore este e-mail: sua senha atual continua valendo.
            </p>
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>
"""
    return subject, text_body, html_body


def send_reset_email(email: str, token: str) -> None:
    """Executado em segundo plano, depois da resposta ao usuário."""
    subject, text_body, html_body = build_email(token)
    sent = email_service.send_email(email, subject, text_body, html_body)

    if not sent and not config.IS_PRODUCTION:
        # Em desenvolvimento, sem SMTP, o link aparece no log para testes.
        logger.info("Link de recuperação (desenvolvimento): %s", reset_link(token))


def request_reset(db: Session, email: str) -> tuple[str, str] | None:
    """
    Processa o pedido. Retorna (email, token) para envio em segundo plano,
    ou None quando não há nada a enviar. Quem chama sempre responde a
    mesma mensagem ao usuário.
    """
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user or user.is_active is False:
        return None

    token = create_reset_token(db, user)
    if not token:
        return None

    return user.email, token


def _valid_token(db: Session, token: str) -> models.PasswordResetToken | None:
    if not token:
        return None

    record = (
        db.query(models.PasswordResetToken)
        .filter(models.PasswordResetToken.token_hash == _hash_token(token))
        .first()
    )

    if not record or record.used_at is not None or record.expires_at < _now():
        return None

    return record


def reset_password(db: Session, token: str, new_password_hash: str) -> bool:
    record = _valid_token(db, token)
    if record is None:
        return False

    user = db.query(models.User).filter(models.User.id == record.user_id).first()
    if not user or user.is_active is False:
        return False

    now = _now()
    user.hashed_password = new_password_hash
    user.password_changed_at = now

    # Este link e todos os outros pendentes do usuário deixam de valer.
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id,
        models.PasswordResetToken.used_at.is_(None),
    ).update({"used_at": now}, synchronize_session=False)

    db.commit()
    logger.info("Senha redefinida pelo link de recuperação para o usuário %s", user.id)
    return True

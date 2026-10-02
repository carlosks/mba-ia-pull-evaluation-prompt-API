from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Plano comercial do usuário.
    # Valores previstos:
    # free, pro, team, admin
    plan = Column(String, nullable=False, default="free")

    # Limite mensal de gerações.
    # Free = 5
    # Pro = 100
    # Team = 1000
    # Admin = -1, ilimitado
    monthly_generation_limit = Column(Integer, nullable=False, default=5)

    # Controle administrativo.
    is_active = Column(Boolean, nullable=False, default=True)
    is_admin = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=utc_now)

    # Aceite dos Termos de Uso e da Política de Privacidade (LGPD).
    terms_version = Column(String, nullable=True)
    terms_accepted_at = Column(DateTime, nullable=True)

    # Tokens de acesso emitidos antes desta data deixam de valer
    # (encerra as sessões abertas quando a senha é trocada).
    password_changed_at = Column(DateTime, nullable=True)

    projects = relationship(
        "Project",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    usage_logs = relationship(
        "UsageLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    bug = Column(Text, nullable=False)
    user_story = Column(Text, nullable=False)
    acceptance_criteria = Column(Text)

    code = Column(Text, nullable=False)

    score = Column(String)
    status = Column(String)

    # Nesta aplicação, zip_path também é usado para armazenar o project_name.
    zip_path = Column(String)

    created_at = Column(DateTime, default=utc_now)

    owner_id = Column(Integer, ForeignKey("users.id"))


    owner = relationship("User", back_populates="projects")


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Endpoint que consumiu uso:
    # /projects/generate
    # /projects/generate-full
    # /projects/generate-solution
    endpoint = Column(String, nullable=False)

    # Nome do projeto gerado, quando existir.
    project_name = Column(String)

    # Status do uso:
    # success, failed, blocked
    status = Column(String, nullable=False, default="success")

    # Consumo do LLM nesta geração (para medir margem por plano).
    model = Column(String)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    cost_usd = Column(Float)
    duration_ms = Column(Integer)

    created_at = Column(DateTime, default=utc_now, index=True)

    user = relationship("User", back_populates="usage_logs")


class GenerationJob(Base):
    """
    Geração executada em segundo plano.

    O cliente cria o job, recebe o id na hora e consulta o status
    até ficar succeeded ou failed. Assim a requisição HTTP não fica
    presa esperando o LLM.
    """

    __tablename__ = "generation_jobs"

    id = Column(String(36), primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # generate | generate-full | generate-solution
    kind = Column(String, nullable=False)

    # queued | running | succeeded | failed
    status = Column(String, nullable=False, default="queued", index=True)

    bug = Column(Text, nullable=False)

    # Resposta completa (JSON) quando succeeded.
    result_json = Column(Text)

    # Mensagem amigável quando failed (sem detalhes internos).
    error_message = Column(Text)

    project_name = Column(String)

    created_at = Column(DateTime, default=utc_now, index=True)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)


class Subscription(Base):
    """
    Assinatura de um plano pago (hoje via Asaas).

    Status:
    - pending:  criada, aguardando o primeiro pagamento
    - active:   pagamento em dia
    - past_due: cobrança vencida; acesso mantido até current_period_end
    - canceled: cancelada; acesso mantido até current_period_end
    """

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    provider = Column(String, nullable=False, default="asaas")
    provider_customer_id = Column(String, index=True)
    provider_subscription_id = Column(String, unique=True, index=True)

    plan = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending", index=True)
    value = Column(Float, nullable=False)

    # Link da fatura atual (Pix, boleto ou cartão, na página da Asaas).
    invoice_url = Column(String)

    current_period_end = Column(DateTime)
    canceled_at = Column(DateTime)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class BillingEvent(Base):
    """
    Evento recebido do provedor de pagamento (webhook).
    A chave primária é o id do evento, o que impede processar o mesmo
    evento duas vezes (a Asaas pode reenviar eventos).
    """

    __tablename__ = "billing_events"

    id = Column(String, primary_key=True)
    provider = Column(String, nullable=False, default="asaas")
    event_type = Column(String, nullable=False, index=True)
    payload = Column(Text, nullable=False)
    processed = Column(Boolean, nullable=False, default=False)
    error = Column(Text)
    received_at = Column(DateTime, default=utc_now, index=True)


class PasswordResetToken(Base):
    """Link de "esqueci minha senha". Guardamos só o hash do token."""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

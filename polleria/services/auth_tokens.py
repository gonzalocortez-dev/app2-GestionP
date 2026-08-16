"""Tokens de verificación y restablecimiento de contraseña."""

from __future__ import annotations

import datetime
import hashlib
import secrets

from sqlmodel import select

from polleria.models import EmailToken, User
from polleria.services.email import (
    is_mail_configured,
    send_password_reset_email,
    send_verification_email,
)
from polleria.utils.time import now_utc

VERIFY_HOURS = 24
RESET_HOURS = 1


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _invalidate_tokens(db, user_id: int, purpose: str) -> None:
    for row in db.exec(
        select(EmailToken).where(
            EmailToken.user_id == user_id,
            EmailToken.purpose == purpose,
            EmailToken.used == False,  # noqa: E712
        )
    ).all():
        row.used = True
        db.add(row)


def _create_token(db, user_id: int, purpose: str, hours: int) -> str:
    raw = secrets.token_urlsafe(32)
    _invalidate_tokens(db, user_id, purpose)
    db.add(
        EmailToken(
            user_id=user_id,
            token_hash=_hash_token(raw),
            purpose=purpose,
            expiration=now_utc() + datetime.timedelta(hours=hours),
            used=False,
        )
    )
    db.commit()
    return raw


def issue_verification(db, user: User) -> None:
    if not is_mail_configured():
        user.email_verified = True
        db.add(user)
        db.commit()
        return
    raw = _create_token(db, user.id, "verify", VERIFY_HOURS)
    send_verification_email(to=user.email, nombre=user.nombre, token=raw)


def issue_password_reset(db, user: User) -> None:
    raw = _create_token(db, user.id, "reset", RESET_HOURS)
    send_password_reset_email(to=user.email, nombre=user.nombre, token=raw)


def consume_token(db, raw: str, purpose: str) -> User | None:
    if not raw.strip():
        return None
    token_hash = _hash_token(raw.strip())
    row = db.exec(
        select(EmailToken).where(
            EmailToken.token_hash == token_hash,
            EmailToken.purpose == purpose,
            EmailToken.used == False,  # noqa: E712
            EmailToken.expiration >= now_utc(),
        )
    ).first()
    if row is None:
        return None
    user = db.get(User, row.user_id)
    if user is None:
        return None
    row.used = True
    db.add(row)
    db.commit()
    return user


def verify_email_token(db, raw: str) -> User | None:
    user = consume_token(db, raw, "verify")
    if user is None:
        return None
    user.email_verified = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def validate_reset_token(db, raw: str) -> User | None:
    if not raw.strip():
        return None
    token_hash = _hash_token(raw.strip())
    row = db.exec(
        select(EmailToken).where(
            EmailToken.token_hash == token_hash,
            EmailToken.purpose == "reset",
            EmailToken.used == False,  # noqa: E712
            EmailToken.expiration >= now_utc(),
        )
    ).first()
    if row is None:
        return None
    return db.get(User, row.user_id)

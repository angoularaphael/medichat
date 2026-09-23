from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.entities import ChatMessage, Conversation


def serialize_conversation(row: Conversation) -> dict:
    return {
        "id": row.id,
        "crew_member_code": row.crew_member_code,
        "created_by": row.created_by,
        "title": row.title,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_conversations(db: Session, username: str, status: str | None = "open") -> list[Conversation]:
    query = db.query(Conversation).filter(Conversation.created_by == username)
    if status:
        query = query.filter(Conversation.status == status)
    return query.order_by(Conversation.updated_at.desc()).all()


def get_conversation(db: Session, conversation_id: str, username: str) -> Conversation | None:
    return (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.created_by == username)
        .first()
    )


def create_conversation(db: Session, username: str, crew_member_code: str) -> Conversation:
    row = Conversation(
        id=str(uuid4()),
        crew_member_code=crew_member_code,
        created_by=username,
        title="Nouvelle conversation",
        status="open",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def archive_conversation(db: Session, conversation_id: str, username: str) -> Conversation | None:
    row = get_conversation(db, conversation_id, username)
    if not row:
        return None
    row.status = "archived"
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def list_messages(db: Session, conversation_id: str) -> list[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )


def serialize_message(row: ChatMessage) -> dict:
    return {
        "id": row.id,
        "conversation_id": row.conversation_id,
        "role": row.role,
        "content": row.content,
        "meta": row.meta,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def history_text(db: Session, conversation_id: str, limit: int = 12) -> str:
    rows = list_messages(db, conversation_id)[-limit:]
    return "\n".join(f"{row.role}: {row.content}" for row in rows)


def touch_title(db: Session, row: Conversation, message: str) -> None:
    if row.title == "Nouvelle conversation":
        cleaned = " ".join(message.split())[:72]
        if cleaned:
            row.title = cleaned
    row.updated_at = datetime.now(timezone.utc)

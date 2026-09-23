from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    statements: list[str] = []
    if "crew_members" in tables:
        cols = {column["name"] for column in inspector.get_columns("crew_members")}
        if "avatar_data" not in cols:
            statements.append("ALTER TABLE crew_members ADD COLUMN avatar_data TEXT")
    if "plant_cultures" in tables:
        cols = {column["name"] for column in inspector.get_columns("plant_cultures")}
        if "description" not in cols:
            statements.append("ALTER TABLE plant_cultures ADD COLUMN description TEXT")
    if "chat_messages" in tables:
        cols = {column["name"] for column in inspector.get_columns("chat_messages")}
        if "conversation_id" not in cols:
            statements.append("ALTER TABLE chat_messages ADD COLUMN conversation_id VARCHAR(36)")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

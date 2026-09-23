from sqlalchemy.orm import Session

from app.models.entities import FaceIdentity, User

MATCH_THRESHOLD = 0.82
DESCRIPTOR_SIZE = 1024


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    norm_left = sum(a * a for a in left) ** 0.5
    norm_right = sum(b * b for b in right) ** 0.5
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return dot / (norm_left * norm_right)


def _clean_descriptor(raw: list) -> list[float]:
    values = [float(item) for item in raw[:DESCRIPTOR_SIZE]]
    if len(values) < 64:
        raise ValueError("Descripteur facial trop court")
    return values


def list_enrollments(db: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in db.query(FaceIdentity).all():
        counts[row.crew_member_code] = counts.get(row.crew_member_code, 0) + 1
    return counts


def enroll(db: Session, crew_member_code: str, descriptor: list, enrolled_by: str) -> FaceIdentity:
    cleaned = _clean_descriptor(descriptor)
    row = FaceIdentity(
        crew_member_code=crew_member_code,
        descriptor=cleaned,
        enrolled_by=enrolled_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def replace_enrollments(db: Session, crew_member_code: str, descriptors: list[list], enrolled_by: str) -> int:
    db.query(FaceIdentity).filter(FaceIdentity.crew_member_code == crew_member_code).delete()
    count = 0
    for item in descriptors:
        db.add(
            FaceIdentity(
                crew_member_code=crew_member_code,
                descriptor=_clean_descriptor(item),
                enrolled_by=enrolled_by,
            )
        )
        count += 1
    db.commit()
    return count


def clear_enrollments(db: Session, crew_member_code: str) -> None:
    db.query(FaceIdentity).filter(FaceIdentity.crew_member_code == crew_member_code).delete()
    db.commit()


def match(db: Session, descriptor: list) -> tuple[User | None, float]:
    probe = _clean_descriptor(descriptor)
    best_user: User | None = None
    best_score = 0.0
    rows = db.query(FaceIdentity).all()
    users = {user.crew_member_code: user for user in db.query(User).filter(User.is_active.is_(True)).all()}
    for row in rows:
        score = _cosine(probe, list(row.descriptor or []))
        if score > best_score:
            best_score = score
            best_user = users.get(row.crew_member_code)
    if best_user and best_score >= MATCH_THRESHOLD:
        return best_user, best_score
    return None, best_score

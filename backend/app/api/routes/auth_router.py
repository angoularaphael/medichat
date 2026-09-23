from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import CrewMember, User
from app.schemas.api import LoginRequest, TokenResponse, UserOut
from app.services.auth import create_access_token, verify_password


router = APIRouter(prefix="/api/auth", tags=["auth"])


def user_out(user: User, member: CrewMember | None = None) -> UserOut:
    return UserOut(
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        crew_member_code=user.crew_member_code,
        allergies=list(member.allergies or []) if member else [],
        avatar_data=member.avatar_data if member else None,
        age=member.age if member else None,
    )


def _member_for(db: Session, user: User) -> CrewMember | None:
    return db.query(CrewMember).filter(CrewMember.code == user.crew_member_code).first()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(User.username == body.username.lower().strip()).first()
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect",
        )
    return TokenResponse(
        access_token=create_access_token(user.username),
        user=user_out(user, _member_for(db, user)),
    )


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    return user_out(user, _member_for(db, user))

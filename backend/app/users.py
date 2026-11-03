from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.deps import get_current_user
from app.exceptions import ApiError
from app.models import User
from app.schemas import UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(default=None, min_length=1, max_length=30)
    avatar_url: str | None = Field(default=None, max_length=2048)


@router.get("/me", response_model=UserResponse)
def get_me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse(user=user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: ProfileUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> UserResponse:
    data = payload.model_dump(exclude_unset=True)

    if "username" in data:
        new_username = (data["username"] or "").strip()
        if not new_username:
            raise ApiError(
                status_code=422,
                detail="Перевірте правильність полів",
                fields={"username": "Нікнейм не може бути порожнім"},
            )
        if new_username.lower() != user.username.lower():
            taken = db.execute(
                select(User.id).where(
                    func.lower(User.username) == new_username.lower(),
                    User.id != user.id,
                )
            ).scalar_one_or_none()
            if taken is not None:
                raise ApiError(
                    status_code=409,
                    detail="Нікнейм вже зайнятий",
                    fields={"username": "Нікнейм вже зайнятий"},
                )
        user.username = new_username

    if "avatar_url" in data:
        value = (data["avatar_url"] or "").strip() or None
        user.avatar_url = value

    db.commit()
    db.refresh(user)
    return UserResponse(user=user)

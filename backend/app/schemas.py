from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterInput(BaseModel):
    email: EmailStr = Field(
        description="Email; унікальний без урахування регістру.",
        examples=["olena@example.com"],
    )
    username: str = Field(
        min_length=3,
        max_length=50,
        description="Нікнейм, 3–50 символів; унікальний без урахування регістру.",
        examples=["olena"],
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Пароль, 8–128 символів.",
        examples=["goodpass1"],
    )


class LoginInput(BaseModel):
    email: EmailStr = Field(
        description="Email, вказаний при реєстрації (регістр не важливий).",
        examples=["olena@example.com"],
    )
    password: str = Field(
        min_length=1, max_length=128, description="Пароль.", examples=["goodpass1"]
    )


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Id користувача.")
    email: EmailStr = Field(description="Email.", examples=["olena@example.com"])
    username: str = Field(description="Нікнейм.", examples=["olena"])
    avatar_url: str | None = Field(
        default=None,
        description="Посилання на аватар; null — аватара немає.",
        examples=["https://example.com/avatar.png"],
    )


class UserResponse(BaseModel):
    user: UserOut = Field(description="Поточний користувач.")

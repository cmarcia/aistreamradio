from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.utilities.auth import hash_password, verify_password


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> models.User | None:
        return self.db.scalar(select(models.User).where(models.User.id == user_id))

    def get_by_email(self, email: str) -> models.User | None:
        return self.db.scalar(select(models.User).where(models.User.email == email.lower().strip()))

    def create_user_with_password(
        self, email: str, raw_password: str, full_name: str | None = None
    ) -> models.User:
        existing = self.get_by_email(email)
        if existing is not None:
            raise ValueError("User with this email already exists")

        hashed = hash_password(raw_password)
        user = models.User(
            email=email.lower().strip(),
            hashed_password=hashed,
            full_name=full_name,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate_with_password(
        self, email: str, raw_password: str
    ) -> models.User | None:
        user = self.get_by_email(email)
        if not user or not user.hashed_password:
            return None
        if verify_password(raw_password, user.hashed_password):
            return user
        return None

    def upsert_from_oauth(self, profile: dict) -> models.User:
        email = profile["email"].lower().strip()
        user = self.get_by_email(email)
        if user is None:
            user = models.User(
                email=email,
                full_name=profile.get("full_name"),
                avatar_url=profile.get("avatar_url"),
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        else:
            if profile.get("avatar_url") and not user.avatar_url:
                user.avatar_url = profile["avatar_url"]
                self.db.commit()
                self.db.refresh(user)
        return user

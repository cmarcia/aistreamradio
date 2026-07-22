from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> models.User | None:
        return self.db.get(models.User, user_id)

    def get_by_email(self, email: str) -> models.User | None:
        return self.db.scalar(
            select(models.User).where(models.User.email == email.strip().lower())
        )

    def get_by_oauth(self, provider: str, provider_user_id: str) -> models.User | None:
        account = self.db.scalar(
            select(models.OAuthAccount).where(
                models.OAuthAccount.provider == provider,
                models.OAuthAccount.provider_user_id == str(provider_user_id),
            )
        )
        if account:
            return account.user
        return None

    def upsert_from_oauth(self, profile: dict) -> models.User:
        """
        Upserts a User and OAuthAccount linkage based on normalized OAuth profile dictionary.
        profile dict format:
          {
            "provider": str,
            "provider_user_id": str,
            "email": str,
            "full_name": str | None,
            "avatar_url": str | None
          }
        """
        provider = profile["provider"]
        provider_user_id = str(profile["provider_user_id"])
        email = profile["email"].strip().lower()
        full_name = profile.get("full_name")
        avatar_url = profile.get("avatar_url")

        # 1. Check if OAuthAccount already exists
        existing_user = self.get_by_oauth(provider, provider_user_id)
        if existing_user:
            # Update missing full_name or avatar_url if needed
            changed = False
            if full_name and not existing_user.full_name:
                existing_user.full_name = full_name
                changed = True
            if avatar_url and not existing_user.avatar_url:
                existing_user.avatar_url = avatar_url
                changed = True
            if changed:
                self.db.commit()
                self.db.refresh(existing_user)
            return existing_user

        # 2. Check if User exists by email
        user = self.get_by_email(email)
        if user is None:
            user = models.User(
                email=email,
                full_name=full_name,
                avatar_url=avatar_url,
            )
            self.db.add(user)
            self.db.flush()

        # 3. Create linked OAuthAccount
        oauth_account = models.OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email_at_provider=email,
        )
        self.db.add(oauth_account)
        self.db.commit()
        self.db.refresh(user)

        return user

    def create_user_with_password(self, email: str, raw_password: str, full_name: str | None = None) -> models.User:
        from app.utilities.auth import hash_password

        email_clean = email.strip().lower()
        if self.get_by_email(email_clean):
            raise ValueError("An account with this email address already exists.")

        user = models.User(
            email=email_clean,
            full_name=full_name.strip() if full_name else None,
            hashed_password=hash_password(raw_password),
            avatar_url=f"https://api.dicebear.com/7.x/bottts/svg?seed={email_clean}",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate_with_password(self, email: str, raw_password: str) -> models.User | None:
        from app.utilities.auth import verify_password

        user = self.get_by_email(email.strip().lower())
        if not user or not user.hashed_password:
            return None
        if verify_password(raw_password, user.hashed_password):
            return user
        return None


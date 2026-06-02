import asyncio
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource

from app.config import SCOPES
from app.repositories.users import UserRepository


class GmailService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def get_service(self, user_id: int) -> Resource | None:
        token_json = await self.user_repo.get_token_json(user_id)
        if not token_json:
            return None

        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)

        if creds.expired and creds.refresh_token:
            await asyncio.to_thread(creds.refresh, Request())
            await self.user_repo.save_token(user_id, creds.to_json())

        return await asyncio.to_thread(build, "gmail", "v1", credentials=creds)

    async def get_profile(self, service: Resource) -> dict:
        return await asyncio.to_thread(
            lambda: service.users().getProfile(userId="me").execute()
        )

    async def init_user_profile(self, user_id: int) -> dict | None:
        service = await self.get_service(user_id)
        if not service:
            return None
        profile = await self.get_profile(service)
        if profile.get("emailAddress"):
            await self.user_repo.set_email(user_id, profile["emailAddress"])
        return profile

    async def get_message_full(self, service: Resource, msg_id: str) -> dict:
        return await asyncio.to_thread(
            lambda: service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()
        )

    async def search_messages(self, service: Resource, query: str, max_results: int = 50) -> dict:
        return await asyncio.to_thread(
            lambda: service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()
        )

import asyncio

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

from app.config import SCOPES, CLIENT_SECRET_FILE, REDIRECT_URI
from app.repositories.users import UserRepository


class OAuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def _flow(self) -> Flow:
        return Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )

    def generate_auth_url(self, user_id: int) -> str:
        flow = self._flow()
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=str(user_id),
        )
        return auth_url

    async def fetch_and_save_token(self, code: str, state: str) -> Credentials:
        user_id = int(state)
        creds = await asyncio.to_thread(self._exchange_code, code)
        await self.user_repo.save_token(user_id, creds.to_json())
        return creds

    def _exchange_code(self, code: str) -> Credentials:
        flow = self._flow()
        flow.fetch_token(code=code)
        return flow.credentials

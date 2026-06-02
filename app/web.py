import logging

from aiohttp import web

from app import texts
from app.services.oauth import OAuthService
from app.services.gmail import GmailService

logger = logging.getLogger(__name__)


def _page(heading: str, hint: str, status: int) -> web.Response:
    html = (
        '<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8">'
        f"<title>{heading}</title></head>"
        '<body style="font-family: sans-serif; text-align: center; padding-top: 80px;">'
        f"<h1>{heading}</h1><p>{hint}</p></body></html>"
    )
    return web.Response(text=html, content_type="text/html", status=status)


class OAuthCallbackApp:
    def __init__(self, oauth_service: OAuthService, gmail_service: GmailService):
        self.oauth_service = oauth_service
        self.gmail_service = gmail_service

    async def _callback(self, request: web.Request) -> web.Response:
        code = request.query.get("code")
        state = request.query.get("state")
        if request.query.get("error") or not code or not state:
            logger.error("OAuth callback без code/state: %s", dict(request.query))
            return _page(texts.WEB_FAIL_TITLE, texts.WEB_FAIL_HINT, 400)
        try:
            user_id = int(state)
            await self.oauth_service.fetch_and_save_token(code, state)
            await self.gmail_service.init_user_profile(user_id)
        except Exception as e:
            logger.error("OAuth callback не удался: %s", e)
            return _page(texts.WEB_FAIL_TITLE, texts.WEB_FAIL_HINT, 500)
        logger.info("Успешная аутентификация для user_id=%s", user_id)
        return _page(texts.WEB_OK_TITLE, texts.WEB_OK_HINT, 200)

    async def start(self, port: int = 8080) -> None:
        app = web.Application()
        app.router.add_get("/oauth2callback", self._callback)
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", port).start()
        logger.info("OAuth-сервер запущен на порту %d", port)

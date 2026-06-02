from app.repositories.users import UserRepository
from app.repositories.subscriptions import SubscriptionRepository
from app.repositories.processed import ProcessedRepository
from app.services.oauth import OAuthService
from app.services.gmail import GmailService
from app.services.scanner import SubscriptionScanner

user_repo = UserRepository()
sub_repo = SubscriptionRepository()
processed_repo = ProcessedRepository()

oauth_service = OAuthService(user_repo)
gmail_service = GmailService(user_repo)
scanner = SubscriptionScanner(gmail_service, sub_repo, processed_repo)

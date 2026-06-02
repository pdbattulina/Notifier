KEYWORDS = [
    "подписка", "подписки", "подписку",
    "продление", "автопродление",
    "списание", "спишется",
    "платёж", "платеж",
    "оплата",
    "счёт", "счет",
    "subscription",
    "renew", "renewal", "renews",
    "payment", "charged",
    "invoice", "receipt",
    "billing",
    "membership",
]

def is_subscription_candidate(subject: str, body: str) -> bool:
    text = f"{subject} {body}".lower()
    return any(kw in text for kw in KEYWORDS)
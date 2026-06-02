import os
import json
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

MODEL = "gemini-3.1-flash-lite"

PROMPT = """
Извлеки данные о подписке из письма. Верни СТРОГО JSON без markdown:
{{
  "service_name": "каноническое короткое имя бренда или null",
  "amount": число суммы планового списания или null,
  "currency": "ISO-код валюты (RUB/USD/EUR) или null",
  "billing_date": "дата следующего списания YYYY-MM-DD или null",
  "billing_period": "monthly/yearly/weekly/unknown",
  "is_subscription": true или false
}}

is_subscription = true ТОЛЬКО если письмо является:
- уведомлением о предстоящем автоматическом продлении подписки с фиксированной суммой
- подтверждением списания за регулярную подписку (Netflix, Spotify, Яндекс Плюс и т.д.)

is_subscription = false если письмо является:
- чеком за разовый платёж или оплату по факту использования (pay-as-you-go)
- счётом за облачные ресурсы, GPU, API-запросы где сумма каждый раз разная
- рекламой или предложением купить подписку
- уведомлением об окончании бесплатного триала
- промо-рассылкой с тарифами и ценами

Важно: бери сумму РЕАЛЬНОГО планового списания, игнорируй рекламные цены.
Если дата без года — используй год из даты письма ({email_date}).
Если поля нет — ставь null, не выдумывай.

service_name — название КОНКРЕТНОЙ услуги, за которую идёт списание; пиши его
всегда ОДИНАКОВО для одной услуги, без доменов (.com) и юр. формы.
Не добавляй уровень тарифа (Premium/Pro/Standard/+) — это тот же сервис.
НО отдельные платные опции и доп-пакеты — это САМОСТОЯТЕЛЬНЫЕ подписки со своим
названием, даже если письмо пришло от общего бренда. Например "Матч Максимум"
(опция Яндекс Плюс) — это отдельная подписка, а не "Яндекс Плюс".
Примеры названий: "Netflix", "Spotify", "Яндекс Плюс", "Матч Максимум", "iCloud".

billing_period: если период явно не указан, но это регулярная подписка —
ставь наиболее вероятный (обычно monthly). unknown используй только если
действительно невозможно определить.

Отправитель: {sender}
Тема: {subject}
Текст: {body}
"""

_client = None

def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY не найден в .env")
        _client = genai.Client(api_key=api_key)
    return _client


def parse_with_gemini(sender: str, subject: str, body: str,
                      email_date: str = "") -> dict | None:
    try:
        prompt = PROMPT.format(
            sender=sender, subject=subject, body=body[:4000],
            email_date=email_date or "неизвестно",
        )
        response = _get_client().models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        data = json.loads(response.text)

        required = {"service_name", "amount", "currency",
                    "billing_date", "billing_period", "is_subscription"}
        if not required.issubset(data.keys()):
            logger.error(f"Gemini вернул неполный JSON: {data}")
            return None

        return data

    except json.JSONDecodeError as e:
        logger.error(f"Gemini вернул невалидный JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Ошибка Gemini API: {e}")
        return None
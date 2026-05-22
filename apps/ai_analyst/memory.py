"""Memory — har bir menejer uchun alohida suhbat tarixi.

LangChain ``ConversationBufferWindowMemory`` (oxirgi N ta almashinuvni
saqlaydigan "oyna" xotirasi) ishlatiladi. Lekin Django so'rovlari holatsiz
(stateless) bo'lgani uchun xotira obyekti har so'rovda yangidan yaratiladi —
shuning uchun u ``ChatMessage`` jadvalidan oldingi xabarlar bilan
to'ldiriladi (hydrate). Natijada server qayta ishga tushsa ham suhbat
tarixi yo'qolmaydi.

Asosiy funksiyalar:
  * :func:`build_memory`   — bazadan to'ldirilgan tayyor memory obyekti.
  * :func:`save_turn`      — yangi savol-javob juftligini bazaga yozish.
  * :func:`history_pairs`  — tarixni ``(savol, javob)`` juftliklari ro'yxati.
  * :func:`history_messages` — tarixni UI uchun lug'atlar ro'yxati.
  * :func:`clear_history`  — menejer tarixini tozalash.
"""
import logging

from .models import ChatMessage

logger = logging.getLogger(__name__)

# Oynaning hajmi — saqlanadigan oxirgi savol-javob almashinuvlari soni.
WINDOW_SIZE = 10


def build_memory(manager_id: int, input_key: str = 'question',
                 output_key: str = 'answer'):
    """Bazadan to'ldirilgan ``ConversationBufferWindowMemory`` qaytaradi.

    Args:
        manager_id: AmoCRM menejer IDsi (umumiy suhbat uchun 0).
        input_key: zanjirga kiruvchi savol kaliti
            (``ConversationalRetrievalChain`` uchun ``question``,
            ``AgentExecutor`` uchun ``input``).
        output_key: zanjir javobining kaliti
            (RAG uchun ``answer``, Agent uchun ``output``).

    Returns:
        Oxirgi ``WINDOW_SIZE`` ta almashinuv bilan to'ldirilgan memory.
    """
    from langchain.memory import ConversationBufferWindowMemory

    memory = ConversationBufferWindowMemory(
        k=WINDOW_SIZE,
        memory_key='chat_history',
        return_messages=True,
        input_key=input_key,
        output_key=output_key,
    )

    # Bazadan oxirgi almashinuvlarni o'qib, memory'ga yuklaymiz.
    for human, ai in history_pairs(manager_id):
        memory.chat_memory.add_user_message(human)
        memory.chat_memory.add_ai_message(ai)

    return memory


def history_pairs(manager_id: int) -> list[tuple[str, str]]:
    """Menejer suhbat tarixini ``(savol, javob)`` juftliklari ko'rinishida qaytaradi.

    Faqat oxirgi ``WINDOW_SIZE`` ta to'liq almashinuv qaytariladi.
    """
    rows = list(
        ChatMessage.objects
        .filter(manager_id=manager_id)
        .order_by('created_at')
    )

    pairs: list[tuple[str, str]] = []
    pending_human = None
    for row in rows:
        if row.role == 'human':
            pending_human = row.content
        elif row.role == 'ai' and pending_human is not None:
            pairs.append((pending_human, row.content))
            pending_human = None

    return pairs[-WINDOW_SIZE:]


def history_messages(manager_id: int) -> list[dict]:
    """Suhbat tarixini UI uchun ``[{role, content, created_at}]`` ko'rinishida qaytaradi."""
    return [
        {
            'role': m.role,
            'content': m.content,
            'created_at': m.created_at.isoformat(),
        }
        for m in ChatMessage.objects.filter(manager_id=manager_id).order_by('created_at')
    ]


def save_turn(manager_id: int, human_text: str, ai_text: str) -> None:
    """Bitta savol-javob almashinuvini bazaga yozadi."""
    ChatMessage.objects.bulk_create([
        ChatMessage(manager_id=manager_id, role='human', content=human_text),
        ChatMessage(manager_id=manager_id, role='ai', content=ai_text),
    ])
    logger.info('Menejer #%s suhbatiga yangi almashinuv saqlandi', manager_id)


def clear_history(manager_id: int) -> int:
    """Menejer suhbat tarixini butunlay o'chiradi. O'chirilgan xabarlar sonini qaytaradi."""
    deleted, _ = ChatMessage.objects.filter(manager_id=manager_id).delete()
    return deleted

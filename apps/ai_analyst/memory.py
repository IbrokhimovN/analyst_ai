import logging

from .models import ChatMessage

logger = logging.getLogger(__name__)

WINDOW_SIZE = 10

def build_memory(manager_id: int, input_key: str = 'question',
                 output_key: str = 'answer'):
    from langchain.memory import ConversationBufferWindowMemory

    memory = ConversationBufferWindowMemory(
        k=WINDOW_SIZE,
        memory_key='chat_history',
        return_messages=True,
        input_key=input_key,
        output_key=output_key,
    )

    for human, ai in history_pairs(manager_id):
        memory.chat_memory.add_user_message(human)
        memory.chat_memory.add_ai_message(ai)

    return memory

def history_pairs(manager_id: int) -> list[tuple[str, str]]:
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
    return [
        {
            'role': m.role,
            'content': m.content,
            'created_at': m.created_at.isoformat(),
        }
        for m in ChatMessage.objects.filter(manager_id=manager_id).order_by('created_at')
    ]

def save_turn(manager_id: int, human_text: str, ai_text: str) -> None:
    ChatMessage.objects.bulk_create([
        ChatMessage(manager_id=manager_id, role='human', content=human_text),
        ChatMessage(manager_id=manager_id, role='ai', content=ai_text),
    ])
    logger.info('Menejer #%s suhbatiga yangi almashinuv saqlandi', manager_id)

def clear_history(manager_id: int) -> int:
    deleted, _ = ChatMessage.objects.filter(manager_id=manager_id).delete()
    return deleted

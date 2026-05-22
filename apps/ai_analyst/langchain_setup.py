"""LangChain umumiy sozlamalari — LLM va embedding fabrikalari.

Bu modul LangChain'ning ikkita asosiy komponentini bitta joydan
ta'minlaydi, shuning uchun RAG (``rag.py``) va Agent (``agent.py``)
bir xil sozlamalardan foydalanadi:

  * :func:`get_llm` — Claude chat modeli (``ChatAnthropic``).
  * :func:`get_embeddings` — matnni vektorga aylantiruvchi model.

Barcha sozlamalar ``.env`` faylidan o'qiladi (``config/settings``):
``ANTHROPIC_API_KEY``, ``LANGCHAIN_CLAUDE_MODEL``, ``EMBEDDINGS_PROVIDER``,
``EMBEDDINGS_MODEL``, ``OPENAI_API_KEY``.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# Bir marta yaratilgan obyektlar shu yerda keshlanadi (qayta-qayta
# yuklamaslik uchun — ayniqsa embedding modeli og'ir bo'ladi).
_llm_cache = {}
_embeddings_cache = None


def get_llm(temperature: float = 0.3, max_tokens: int = 2000):
    """Claude chat modelini (``ChatAnthropic``) qaytaradi.

    Args:
        temperature: javob ijodkorligi (0 — aniq, 1 — erkin).
        max_tokens: javobning maksimal uzunligi.

    Returns:
        ``langchain_anthropic.ChatAnthropic`` obyekti.
    """
    from langchain_anthropic import ChatAnthropic

    key = (temperature, max_tokens)
    if key not in _llm_cache:
        _llm_cache[key] = ChatAnthropic(
            model=settings.LANGCHAIN_CLAUDE_MODEL,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        logger.info('ChatAnthropic yaratildi: %s', settings.LANGCHAIN_CLAUDE_MODEL)
    return _llm_cache[key]


def get_embeddings():
    """Embedding modelini ``.env`` sozlamasiga qarab qaytaradi.

    ``EMBEDDINGS_PROVIDER`` qiymatiga ko'ra:

      * ``fastembed``    — lokal ONNX modeli (tavsiya, API kalit kerak emas).
      * ``huggingface``  — ``sentence-transformers`` (torch talab qiladi).
      * ``openai``       — OpenAI API (``OPENAI_API_KEY`` kerak).

    Natija keshlanadi — model faqat bir marta xotiraga yuklanadi.
    """
    global _embeddings_cache
    if _embeddings_cache is not None:
        return _embeddings_cache

    provider = (settings.EMBEDDINGS_PROVIDER or 'fastembed').lower()

    if provider == 'fastembed':
        # Lokal ONNX — torch kerak emas, API kalitsiz ishlaydi.
        from langchain_community.embeddings import FastEmbedEmbeddings
        _embeddings_cache = FastEmbedEmbeddings(model_name=settings.EMBEDDINGS_MODEL)

    elif provider == 'huggingface':
        # sentence-transformers (torch). Og'ir, lekin sifatli.
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings_cache = HuggingFaceEmbeddings(model_name=settings.EMBEDDINGS_MODEL)

    elif provider == 'openai':
        # OpenAI bulutli embeddinglari.
        from langchain_openai import OpenAIEmbeddings
        if not settings.OPENAI_API_KEY:
            raise RuntimeError('EMBEDDINGS_PROVIDER=openai, lekin OPENAI_API_KEY .env da yo\'q.')
        _embeddings_cache = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)

    else:
        raise RuntimeError(f'Noma\'lum EMBEDDINGS_PROVIDER: {provider}')

    logger.info('Embeddings yaratildi: provider=%s, model=%s',
                provider, settings.EMBEDDINGS_MODEL)
    return _embeddings_cache

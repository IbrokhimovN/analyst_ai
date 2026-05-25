import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_llm_cache = {}
_embeddings_cache = None

def get_llm(temperature: float = 0.3, max_tokens: int = 2000):
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
    global _embeddings_cache
    if _embeddings_cache is not None:
        return _embeddings_cache

    provider = (settings.EMBEDDINGS_PROVIDER or 'fastembed').lower()

    if provider == 'fastembed':
        from langchain_community.embeddings import FastEmbedEmbeddings
        _embeddings_cache = FastEmbedEmbeddings(model_name=settings.EMBEDDINGS_MODEL)

    elif provider == 'huggingface':
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings_cache = HuggingFaceEmbeddings(model_name=settings.EMBEDDINGS_MODEL)

    elif provider == 'openai':
        from langchain_openai import OpenAIEmbeddings
        if not settings.OPENAI_API_KEY:
            raise RuntimeError('EMBEDDINGS_PROVIDER=openai, lekin OPENAI_API_KEY .env da yo\'q.')
        _embeddings_cache = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)

    else:
        raise RuntimeError(f'Noma\'lum EMBEDDINGS_PROVIDER: {provider}')

    logger.info('Embeddings yaratildi: provider=%s, model=%s',
                provider, settings.EMBEDDINGS_MODEL)
    return _embeddings_cache

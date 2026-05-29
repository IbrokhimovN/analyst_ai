import asyncio
import hashlib
import logging
import re

import edge_tts
from django.core.cache import cache

logger = logging.getLogger(__name__)

DEFAULT_VOICE = 'uz-UZ-SardorNeural'
CACHE_TTL_SECONDS = 60 * 60 * 24 * 7
MAX_TEXT_LENGTH = 2000


def _cache_key(text, voice):
    digest = hashlib.sha256((voice + '|' + text).encode('utf-8')).hexdigest()
    return f'tts:{digest}'


_MARKDOWN_LINK_RE = re.compile(r'\[([^\]]+)\]\([^)]+\)')
_CODE_BLOCK_RE = re.compile(r'```[\s\S]*?```')
_INLINE_CODE_RE = re.compile(r'`([^`]+)`')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_BULLET_RE = re.compile(r'^[\-\*\+]\s+', re.MULTILINE)
_BOLD_ITALIC_RE = re.compile(r'\*{1,3}([^*]+)\*{1,3}')
_EMOJI_KEEP_RE = re.compile(r'[^\w\sа-яА-ЯёўғҳқўЎҒҲҚ.,!?;:\'\"-]', re.UNICODE)


def clean_text_for_tts(text):
    if not text:
        return ''
    text = _CODE_BLOCK_RE.sub(' ', text)
    text = _INLINE_CODE_RE.sub(r'\1', text)
    text = _MARKDOWN_LINK_RE.sub(r'\1', text)
    text = _HEADING_RE.sub('', text)
    text = _BULLET_RE.sub('', text)
    text = _BOLD_ITALIC_RE.sub(r'\1', text)
    text = re.sub(r'\n{2,}', '. ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH].rstrip() + '...'
    return text


async def _synthesize_async(text, voice):
    communicate = edge_tts.Communicate(text, voice)
    chunks = []
    async for chunk in communicate.stream():
        if chunk.get('type') == 'audio':
            chunks.append(chunk['data'])
    return b''.join(chunks)


def synthesize(text, voice=DEFAULT_VOICE):
    cleaned = clean_text_for_tts(text)
    if not cleaned:
        return None

    key = _cache_key(cleaned, voice)
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        audio = asyncio.run(_synthesize_async(cleaned, voice))
    except Exception as exc:
        logger.warning('Edge TTS synthesis failed: %s', exc)
        return None

    if audio:
        cache.set(key, audio, timeout=CACHE_TTL_SECONDS)
    return audio

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


_UZ_ONES = [
    '', 'bir', 'ikki', 'uch', "to'rt", 'besh',
    'olti', 'yetti', 'sakkiz', "to'qqiz",
]
_UZ_TENS = [
    '', "o'n", 'yigirma', "o'ttiz", 'qirq', 'ellik',
    'oltmish', 'yetmish', 'sakson', "to'qson",
]
_UZ_SCALES = [
    (10 ** 12, 'trillion'),
    (10 ** 9, 'milliard'),
    (10 ** 6, 'million'),
    (10 ** 3, 'ming'),
    (10 ** 2, 'yuz'),
]


def _uz_under_hundred(n):
    if n == 0:
        return ''
    if n < 10:
        return _UZ_ONES[n]
    tens, ones = divmod(n, 10)
    if ones == 0:
        return _UZ_TENS[tens]
    return _UZ_TENS[tens] + ' ' + _UZ_ONES[ones]


def uz_number_to_words(n):
    if n is None:
        return ''
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if n == 0:
        return 'nol'
    sign = ''
    if n < 0:
        sign = 'minus '
        n = -n
    parts = []
    for value, name in _UZ_SCALES:
        if n >= value:
            count = n // value
            n = n % value
            if value == 100:
                if count == 1:
                    parts.append('yuz')
                else:
                    parts.append(_UZ_ONES[count] + ' yuz')
            elif value == 1000 and count == 1:
                parts.append('ming')
            else:
                parts.append(uz_number_to_words(count) + ' ' + name)
    if n > 0:
        parts.append(_uz_under_hundred(n))
    return sign + ' '.join(p for p in parts if p)


_EMOJI_RE = re.compile(
    '['
    '\U0001F300-\U0001FAFF'
    '\U00002600-\U000027BF'
    '\U0001F000-\U0001F2FF'
    '\U0001F600-\U0001F64F'
    '\U0001F680-\U0001F6FF'
    '\U0001F900-\U0001F9FF'
    '⌀-⏿'
    '⬀-⯿'
    '　-〿'
    ']+',
    flags=re.UNICODE,
)

_MARKDOWN_LINK_RE = re.compile(r'\[([^\]]+)\]\([^)]+\)')
_CODE_BLOCK_RE = re.compile(r'```[\s\S]*?```')
_INLINE_CODE_RE = re.compile(r'`([^`]+)`')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_BULLET_RE = re.compile(r'^[\-\*\+•]\s+', re.MULTILINE)
_BOLD_ITALIC_RE = re.compile(r'\*{1,3}([^*]+)\*{1,3}')
_SPECIAL_CHARS_RE = re.compile(r'[\(\)\[\]\{\}<>«»\|/\\~_=>\^]')
_ARROWS_RE = re.compile(r'[→←↑↓➜➝➞➔]')

_ENGLISH_TO_UZBEK = {
    'call': "qo'ng'iroq",
    'calls': "qo'ng'iroqlar",
    'conversation': 'suhbat',
    'conversations': 'suhbatlar',
    'conversion': 'konversiya',
    'conversions': 'konversiyalar',
    'lead': 'lid',
    'leads': 'lidlar',
    'deal': 'bitim',
    'deals': 'bitimlar',
    'funnel': 'voronka',
    'pipeline': 'voronka',
    'revenue': 'tushum',
    'manager': 'menejer',
    'managers': 'menejerlar',
    'source': 'manba',
    'sources': 'manbalar',
    'status': 'holat',
    'dashboard': 'boshqaruv paneli',
    'followup': 'kuzatuv',
    'follow-up': 'kuzatuv',
    'loss': 'yo\'qotish',
    'top': 'eng yaxshi',
    'best': 'eng yaxshi',
    'average': "o'rtacha",
    'avg': "o'rtacha",
    'total': 'jami',
    'subtotal': 'oraliq jami',
    'month': 'oy',
    'week': 'hafta',
    'day': 'kun',
    'year': 'yil',
    'today': 'bugun',
    'yesterday': 'kecha',
    'crm': 'se er em',
    'amocrm': 'amo se er em',
    'kpi': 'ke pi ay',
    'roi': 'ro i',
    'sum': "so'm",
    'usd': 'dollar',
    'eur': 'yevro',
    'rub': 'rubl',
}

_NUMBER_RE = re.compile(r'-?\d[\d\s,]*\d|-?\d')
_PERCENT_RE = re.compile(r'(-?\d+(?:[.,]\d+)?)\s*%')
_CURRENCY_SUM_RE = re.compile(
    r'(-?\d+(?:[\s,]\d{3})*)\s*(?:so\'?m|sum|som)',
    re.IGNORECASE,
)
_DOLLAR_RE = re.compile(r'\$\s*(-?\d+(?:[\s,]\d{3})*(?:\.\d+)?)')


def _normalize_number(match_str):
    cleaned = match_str.replace(' ', '').replace(',', '')
    try:
        return int(cleaned)
    except ValueError:
        return None


def _replace_number(match):
    n = _normalize_number(match.group(0))
    if n is None:
        return match.group(0)
    return ' ' + uz_number_to_words(n) + ' '


def _replace_percent(match):
    n = _normalize_number(match.group(1).split('.')[0].split(',')[0])
    if n is None:
        return match.group(0)
    return ' ' + uz_number_to_words(n) + ' foiz '


def _replace_sum(match):
    n = _normalize_number(match.group(1))
    if n is None:
        return match.group(0)
    return ' ' + uz_number_to_words(n) + " so'm "


def _replace_dollar(match):
    cleaned = match.group(1).replace(' ', '').replace(',', '').split('.')[0]
    try:
        n = int(cleaned)
    except ValueError:
        return match.group(0)
    return ' ' + uz_number_to_words(n) + ' dollar '


def _replace_english_terms(text):
    def repl(match):
        word = match.group(0).lower()
        return _ENGLISH_TO_UZBEK.get(word, match.group(0))

    pattern = re.compile(
        r'\b(' + '|'.join(re.escape(k) for k in _ENGLISH_TO_UZBEK) + r')\b',
        re.IGNORECASE,
    )
    return pattern.sub(repl, text)


def clean_text_for_tts(text):
    if not text:
        return ''
    text = _CODE_BLOCK_RE.sub(' ', text)
    text = _INLINE_CODE_RE.sub(r'\1', text)
    text = _MARKDOWN_LINK_RE.sub(r'\1', text)
    text = _HEADING_RE.sub('', text)
    text = _BULLET_RE.sub('', text)
    text = _BOLD_ITALIC_RE.sub(r'\1', text)
    text = _EMOJI_RE.sub(' ', text)
    text = _ARROWS_RE.sub(' ', text)

    text = _PERCENT_RE.sub(_replace_percent, text)
    text = _DOLLAR_RE.sub(_replace_dollar, text)
    text = _CURRENCY_SUM_RE.sub(_replace_sum, text)
    text = _NUMBER_RE.sub(_replace_number, text)

    text = _replace_english_terms(text)

    text = _SPECIAL_CHARS_RE.sub(' ', text)
    text = re.sub(r'\n{2,}', '. ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
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

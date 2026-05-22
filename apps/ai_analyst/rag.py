"""RAG — hujjatlar asosida savol-javob (Retrieval-Augmented Generation).

Jarayon:

  1. Foydalanuvchi PDF/Excel fayl yuklaydi (``add_document``).
  2. Fayl ``loaders.py`` orqali matn bo'laklariga ajratiladi.
  3. Bo'laklar embedding'ga aylantirilib **FAISS** lokal vektor omboriga
     saqlanadi (``settings.FAISS_INDEX_DIR``).
  4. Savol berilganda (``answer_question``) tegishli bo'laklar topiladi va
     LangChain **ConversationalRetrievalChain** orqali Claude'ga uzatiladi.
     Suhbat tarixi (Memory) hisobga olinadi.

Agar hech qanday hujjat yuklanmagan bo'lsa, ``answer_question`` oddiy
suhbat rejimiga (faqat Claude + Memory) o'tadi.
"""
import logging
import threading

from django.conf import settings

from . import memory as memory_mod
from .langchain_setup import get_embeddings, get_llm

logger = logging.getLogger(__name__)

# FAISS indeksini bir vaqtda bir nechta so'rov yozib buzmasligi uchun qulf.
_INDEX_LOCK = threading.Lock()

# Retriever bitta savol uchun nechta bo'lak qaytaradi.
RETRIEVER_K = 4

# RAG javob shabloni — Claude hujjat konteksti asosida o'zbekcha javob beradi.
_QA_TEMPLATE = """Siz korxona hujjatlari asosida javob beruvchi yordamchisiz.
Quyidagi kontekstdan foydalanib savolga o'zbek tilida aniq va qisqa javob bering.
Agar javob kontekstda bo'lmasa, "Hujjatlarda bu haqda ma'lumot topilmadi" deb ayting.

Kontekst:
{context}

Savol: {question}
Javob:"""


def _index_dir() -> str:
    """FAISS indeksi saqlanadigan papka yo'li (kerak bo'lsa yaratiladi)."""
    path = settings.FAISS_INDEX_DIR
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def index_exists() -> bool:
    """FAISS indeksi diskda mavjudligini tekshiradi."""
    return (settings.FAISS_INDEX_DIR / 'index.faiss').exists()


def _load_vectorstore():
    """Diskdagi FAISS vektor omborini yuklaydi (mavjud bo'lmasa ``None``)."""
    if not index_exists():
        return None
    from langchain_community.vectorstores import FAISS

    return FAISS.load_local(
        _index_dir(),
        get_embeddings(),
        # Indeks o'zimiz yaratgan ishonchli fayl — deserializatsiyaga ruxsat.
        allow_dangerous_deserialization=True,
    )


def add_document(doc) -> int:
    """Yuklangan ``KnowledgeDocument`` ni FAISS omboriga qo'shadi.

    Fayl bo'laklarga ajratiladi, embedding'ga aylantiriladi va mavjud
    indeksga qo'shiladi (indeks bo'lmasa — yangidan yaratiladi).

    Args:
        doc: ``KnowledgeDocument`` obyekti.

    Returns:
        Qo'shilgan bo'laklar soni.
    """
    from langchain_community.vectorstores import FAISS

    from .loaders import load_file_to_chunks

    chunks = load_file_to_chunks(doc.file.path, doc.id, doc.title)
    if not chunks:
        raise ValueError('Fayldan matn ajratib bo\'lmadi (bo\'sh hujjat).')

    embeddings = get_embeddings()
    with _INDEX_LOCK:
        store = _load_vectorstore()
        if store is None:
            store = FAISS.from_documents(chunks, embeddings)
        else:
            store.add_documents(chunks)
        store.save_local(_index_dir())

    logger.info('Hujjat #%s FAISS indeksiga qo\'shildi: %s bo\'lak', doc.id, len(chunks))
    return len(chunks)


def rebuild_index() -> int:
    """FAISS indeksini barcha "tayyor" hujjatlardan qaytadan quradi.

    Hujjat o'chirilganda chaqiriladi — chunki FAISS'dan bitta hujjatni
    olib tashlash uchun indeksni qayta qurish eng ishonchli yo'l.

    Returns:
        Indeksga joylangan jami bo'laklar soni.
    """
    from langchain_community.vectorstores import FAISS

    from .loaders import load_file_to_chunks
    from .models import KnowledgeDocument

    all_chunks = []
    for doc in KnowledgeDocument.objects.filter(status='ready'):
        try:
            all_chunks.extend(load_file_to_chunks(doc.file.path, doc.id, doc.title))
        except Exception as exc:  # noqa: BLE001
            logger.error('Hujjat #%s qayta qurishda o\'tkazib yuborildi: %s', doc.id, exc)

    with _INDEX_LOCK:
        if all_chunks:
            store = FAISS.from_documents(all_chunks, get_embeddings())
            store.save_local(_index_dir())
        else:
            # Hujjat qolmadi — indeks fayllarini o'chiramiz.
            for fname in ('index.faiss', 'index.pkl'):
                fpath = settings.FAISS_INDEX_DIR / fname
                if fpath.exists():
                    fpath.unlink()

    logger.info('FAISS indeksi qayta qurildi: %s bo\'lak', len(all_chunks))
    return len(all_chunks)


def _answer_with_rag(question: str, manager_id: int) -> dict:
    """ConversationalRetrievalChain orqali hujjatlardan javob oladi."""
    from langchain.chains import ConversationalRetrievalChain
    from langchain.prompts import PromptTemplate

    store = _load_vectorstore()
    retriever = store.as_retriever(search_kwargs={'k': RETRIEVER_K})

    # Memory — shu menejerning suhbat tarixi bilan to'ldiriladi.
    mem = memory_mod.build_memory(manager_id, input_key='question', output_key='answer')

    chain = ConversationalRetrievalChain.from_llm(
        llm=get_llm(),
        retriever=retriever,
        memory=mem,
        return_source_documents=True,
        combine_docs_chain_kwargs={
            'prompt': PromptTemplate(
                template=_QA_TEMPLATE,
                input_variables=['context', 'question'],
            ),
        },
    )

    result = chain.invoke({'question': question})
    answer = result['answer']

    # Javob manbalarini (qaysi hujjatdan olingani) yig'amiz.
    sources = []
    seen = set()
    for doc in result.get('source_documents', []):
        src = doc.metadata.get('source', 'Noma\'lum')
        if src not in seen:
            seen.add(src)
            sources.append(src)

    return {'answer': answer, 'sources': sources, 'used_rag': True}


def _answer_plain(question: str, manager_id: int) -> dict:
    """Hujjat bo'lmaganda — oddiy suhbat rejimi (Claude + Memory)."""
    from langchain_core.messages import HumanMessage, SystemMessage

    # Memory orqali shu menejerning oldingi xabarlarini olamiz.
    mem = memory_mod.build_memory(manager_id, input_key='question', output_key='answer')

    messages = [SystemMessage(content=(
        'Siz savdo bo\'limiga yordam beruvchi professional AI tahlilchisiz. '
        'Javoblarni o\'zbek tilida, qisqa va amaliy bering.'
    ))]
    messages.extend(mem.chat_memory.messages)      # oldingi suhbat
    messages.append(HumanMessage(content=question))

    answer = get_llm().invoke(messages).content
    return {'answer': answer, 'sources': [], 'used_rag': False}


def answer_question(question: str, manager_id: int = 0) -> dict:
    """Foydalanuvchi savoliga javob beradi va suhbat tarixini saqlaydi.

    Hujjatlar mavjud bo'lsa RAG (ConversationalRetrievalChain) ishlatiladi,
    aks holda oddiy Claude suhbati. Har ikkala holatda ham menejerning
    suhbat tarixi (Memory) hisobga olinadi va yangilanadi.

    Args:
        question: foydalanuvchi savoli.
        manager_id: menejer IDsi (umumiy suhbat uchun 0).

    Returns:
        ``{'answer': str, 'sources': list[str], 'used_rag': bool}``.
    """
    question = (question or '').strip()
    if not question:
        return {'answer': 'Savol bo\'sh.', 'sources': [], 'used_rag': False}

    if index_exists():
        result = _answer_with_rag(question, manager_id)
    else:
        result = _answer_plain(question, manager_id)

    # Suhbat tarixini bazaga saqlaymiz (Memory keyingi savolda ishlatadi).
    memory_mod.save_turn(manager_id, question, result['answer'])
    return result

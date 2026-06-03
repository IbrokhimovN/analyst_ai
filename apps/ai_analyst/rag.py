import logging
import threading

from django.conf import settings

from . import memory as memory_mod
from .langchain_setup import get_embeddings, get_llm

logger = logging.getLogger(__name__)

_INDEX_LOCK = threading.Lock()

RETRIEVER_K = 4

_QA_TEMPLATE = """Siz korxona hujjatlari asosida javob beruvchi yordamchisiz.
Quyidagi kontekstdan foydalanib savolga o'zbek tilida aniq va qisqa javob bering.
Agar javob kontekstda bo'lmasa, "Hujjatlarda bu haqda ma'lumot topilmadi" deb ayting.

Kontekst:
{context}

Savol: {question}
Javob:"""

def _index_dir() -> str:
    path = settings.FAISS_INDEX_DIR
    path.mkdir(parents=True, exist_ok=True)
    return str(path)

def index_exists() -> bool:
    return (settings.FAISS_INDEX_DIR / 'index.faiss').exists()

def _load_vectorstore():
    if not index_exists():
        return None
    from langchain_community.vectorstores import FAISS

    return FAISS.load_local(
        _index_dir(),
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )

def add_document(doc) -> int:
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

def add_texts(texts, metadatas) -> int:
    """Tayyor matnlarni (masalan AI hisobotlar) FAISS indeksiga qo'shadi."""
    from langchain_community.vectorstores import FAISS

    embeddings = get_embeddings()
    with _INDEX_LOCK:
        store = _load_vectorstore()
        if store is None:
            store = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
        else:
            store.add_texts(texts, metadatas=metadatas)
        store.save_local(_index_dir())
    return len(texts)

def rebuild_index() -> int:
    from langchain_community.vectorstores import FAISS

    from .loaders import load_file_to_chunks
    from .models import KnowledgeDocument

    all_chunks = []
    for doc in KnowledgeDocument.objects.filter(status='ready'):
        try:
            all_chunks.extend(load_file_to_chunks(doc.file.path, doc.id, doc.title))
        except Exception as exc:
            logger.error('Hujjat #%s qayta qurishda o\'tkazib yuborildi: %s', doc.id, exc)

    with _INDEX_LOCK:
        if all_chunks:
            store = FAISS.from_documents(all_chunks, get_embeddings())
            store.save_local(_index_dir())
        else:
            for fname in ('index.faiss', 'index.pkl'):
                fpath = settings.FAISS_INDEX_DIR / fname
                if fpath.exists():
                    fpath.unlink()

    logger.info('FAISS indeksi qayta qurildi: %s bo\'lak', len(all_chunks))
    return len(all_chunks)

def _answer_with_rag(question: str, manager_id: int) -> dict:
    from langchain.chains import ConversationalRetrievalChain
    from langchain.prompts import PromptTemplate

    store = _load_vectorstore()
    retriever = store.as_retriever(search_kwargs={'k': RETRIEVER_K})

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

    sources = []
    seen = set()
    for doc in result.get('source_documents', []):
        src = doc.metadata.get('source', 'Noma\'lum')
        if src not in seen:
            seen.add(src)
            sources.append(src)

    return {'answer': answer, 'sources': sources, 'used_rag': True}

def _answer_plain(question: str, manager_id: int) -> dict:
    from langchain_core.messages import HumanMessage, SystemMessage

    mem = memory_mod.build_memory(manager_id, input_key='question', output_key='answer')

    messages = [SystemMessage(content=(
        'Siz savdo bo\'limiga yordam beruvchi professional AI tahlilchisiz. '
        'Javoblarni o\'zbek tilida, qisqa va amaliy bering.'
    ))]
    messages.extend(mem.chat_memory.messages)
    messages.append(HumanMessage(content=question))

    answer = get_llm().invoke(messages).content
    return {'answer': answer, 'sources': [], 'used_rag': False}

def answer_question(question: str, manager_id: int = 0) -> dict:
    question = (question or '').strip()
    if not question:
        return {'answer': 'Savol bo\'sh.', 'sources': [], 'used_rag': False}

    if index_exists():
        result = _answer_with_rag(question, manager_id)
    else:
        result = _answer_plain(question, manager_id)

    memory_mod.save_turn(manager_id, question, result['answer'])
    return result

"""Fayl yuklovchilar — PDF va Excel hujjatlarni matn bo'laklariga ajratish.

RAG jarayonining birinchi bosqichi: foydalanuvchi yuklagan faylni o'qib,
uni kichik matn bo'laklariga (``chunk``) ajratish. Keyin bu bo'laklar
``rag.py`` orqali FAISS vektor omboriga joylanadi.

Qo'llab-quvvatlanadigan formatlar:
  * ``.pdf``           — ``PyPDFLoader`` orqali sahifama-sahifa.
  * ``.xlsx`` / ``.xls`` — ``pandas`` orqali, har bir qator matnga aylanadi.
  * ``.csv``           — ``pandas`` orqali.
"""
import logging
import os

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Bitta bo'lak hajmi va bo'laklar orasidagi ustma-ustlik (kontekst yo'qolmasligi uchun).
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def _load_pdf(path: str) -> list[Document]:
    """PDF faylni sahifalarga ajratib ``Document`` ro'yxati sifatida o'qiydi."""
    from langchain_community.document_loaders import PyPDFLoader

    return PyPDFLoader(path).load()


def _load_table(path: str) -> list[Document]:
    """Excel/CSV faylni o'qib, har bir qatorni matn ko'rinishiga keltiradi.

    Har bir qator ``ustun: qiymat | ustun: qiymat`` formatida yoziladi,
    shunda LLM jadval ma'lumotini tushunadi.
    """
    import pandas as pd

    ext = os.path.splitext(path)[1].lower()
    if ext == '.csv':
        sheets = {'CSV': pd.read_csv(path)}
    else:
        # Excel — barcha varaqlarni o'qiymiz.
        sheets = pd.read_excel(path, sheet_name=None)

    documents: list[Document] = []
    for sheet_name, df in sheets.items():
        df = df.fillna('')
        lines = []
        for _, row in df.iterrows():
            cells = [f'{col}: {val}' for col, val in row.items() if str(val).strip()]
            if cells:
                lines.append(' | '.join(cells))
        if lines:
            documents.append(Document(
                page_content=f'Varaq: {sheet_name}\n' + '\n'.join(lines),
                metadata={'sheet': sheet_name},
            ))
    return documents


def load_file_to_chunks(path: str, doc_id: int, title: str) -> list[Document]:
    """Faylni o'qib, FAISS uchun tayyor matn bo'laklarini qaytaradi.

    Args:
        path: fayl joylashgan to'liq yo'l.
        doc_id: ``KnowledgeDocument`` IDsi — har bir bo'lak metadata'siga yoziladi.
        title: hujjat sarlavhasi — javob manbalarini ko'rsatishda ishlatiladi.

    Returns:
        ``Document`` bo'laklari ro'yxati. Har birida ``metadata`` mavjud:
        ``{'doc_id', 'source'}``.

    Raises:
        ValueError: fayl turi qo'llab-quvvatlanmasa.
    """
    ext = os.path.splitext(path)[1].lower()

    if ext == '.pdf':
        raw_docs = _load_pdf(path)
    elif ext in ('.xlsx', '.xls', '.csv'):
        raw_docs = _load_table(path)
    else:
        raise ValueError(f'Qo\'llab-quvvatlanmaydigan fayl turi: {ext}')

    # Hujjatlarni kichik bo'laklarga ajratamiz.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=['\n\n', '\n', '. ', ' ', ''],
    )
    chunks = splitter.split_documents(raw_docs)

    # Har bir bo'lakka manba metadata'sini qo'shamiz.
    for chunk in chunks:
        chunk.metadata['doc_id'] = doc_id
        chunk.metadata['source'] = title

    logger.info('Hujjat #%s "%s" → %s bo\'lak', doc_id, title, len(chunks))
    return chunks

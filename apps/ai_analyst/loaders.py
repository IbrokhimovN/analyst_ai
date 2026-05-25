import logging
import os

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

def _load_pdf(path: str) -> list[Document]:
    from langchain_community.document_loaders import PyPDFLoader

    return PyPDFLoader(path).load()

def _load_table(path: str) -> list[Document]:
    import pandas as pd

    ext = os.path.splitext(path)[1].lower()
    if ext == '.csv':
        sheets = {'CSV': pd.read_csv(path)}
    else:
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
    ext = os.path.splitext(path)[1].lower()

    if ext == '.pdf':
        raw_docs = _load_pdf(path)
    elif ext in ('.xlsx', '.xls', '.csv'):
        raw_docs = _load_table(path)
    else:
        raise ValueError(f'Qo\'llab-quvvatlanmaydigan fayl turi: {ext}')

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=['\n\n', '\n', '. ', ' ', ''],
    )
    chunks = splitter.split_documents(raw_docs)

    for chunk in chunks:
        chunk.metadata['doc_id'] = doc_id
        chunk.metadata['source'] = title

    logger.info('Hujjat #%s "%s" → %s bo\'lak', doc_id, title, len(chunks))
    return chunks

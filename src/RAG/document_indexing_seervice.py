from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger


class DocumentIndexingService:

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_and_split_pdf(self, user_id: int, file_path: Path) -> list[Document]:

        loader = PyPDFLoader(file_path=file_path)
        doc = loader.load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        doc_split = splitter.split_documents(doc)

        for doc in doc_split:
            doc.metadata["user_id"] = user_id

        logger.info("Splitted DOC into chunks")
        return doc_split

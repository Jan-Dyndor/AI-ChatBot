from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentIndexingService:
    #! Moze zrobic z tego classmethod jak i tak nie potrzeuje instacji
    def load_and_split_pdf(self, user_id: int, file_path: Path) -> list[Document]:

        loader = PyPDFLoader(file_path=file_path)
        doc = loader.load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
        )

        doc_split = splitter.split_documents(doc)

        for doc in doc_split:
            doc.metadata["user_id"] = user_id

        return doc_split

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
        """Load a PDF file, split its content into chunks, and assign user metadata.

        Args:
            user_id (int): ID of the user who owns the document.
            file_path (Path): Path to the PDF file to be processed.

        Returns:
            list[Document]: List of document chunks containing text, original
                document metadata, and the associated user ID.

        Notes:
            Uses PyPDFLoader to extract PDF content and
            RecursiveCharacterTextSplitter to split it into chunks based on
            the configured chunk size and overlap.

            Each chunk is assigned a user_id in its metadata to enable
            user-specific filtering during vector similarity search.
        """

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

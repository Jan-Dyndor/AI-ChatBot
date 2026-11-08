from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger


class DocumentIndexingService:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_and_split_pdf(
        self, user_id: int, file_path: Path, file_db_id: int
    ) -> tuple[list[Document], list[str]]:
        """Load a PDF, split it into chunks, and generate unique chunk identifiers.

        Extracts text from the PDF using PyPDFLoader and splits it into chunks
        using RecursiveCharacterTextSplitter with the configured chunk size
        and overlap.

        Each chunk is assigned user_id and file_id metadata to support
        user-specific filtering and document management in the vector database.
        Unique chunk IDs are generated using the file database ID and chunk index.

        Args:
            user_id (int): ID of the user who owns the document.
            file_path (Path): Path to the PDF file to be processed.
            file_db_id (int): ID of the file record in the application database.

        Returns:
            tuple[list[Document], list[str]]: A tuple containing:
                - List of document chunks with user and file metadata.
                - List of unique chunk IDs in the format "{file_db_id}_{index}",
                  corresponding to the document chunks in the same order.
        """

        loader = PyPDFLoader(file_path=file_path)
        doc = loader.load()
        logger.info("Loaded file")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        doc_split = splitter.split_documents(doc)

        for doc in doc_split:
            doc.metadata["user_id"] = user_id
            doc.metadata["file_id"] = file_db_id

        ids = [f"{file_db_id}_{i}" for i in range(len(doc_split))]

        logger.info("Splitted DOC into chunks")
        return doc_split, ids

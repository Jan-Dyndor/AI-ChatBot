from pathlib import Path

from langchain_core.vectorstores import VectorStore

from RAG.document_indexing_seervice import DocumentIndexingService


class FileVectorStorage:
    def __init__(
        self, vector_db: VectorStore, file_index_service: DocumentIndexingService
    ) -> None:
        self.vector_storage = vector_db
        self.index_service = file_index_service

    def add_document(self, file_path: Path, user_id: int):
        doc_chunks = self.index_service.load_and_split_pdf(
            file_path=file_path, user_id=user_id
        )
        self.vector_storage.add_documents(documents=doc_chunks)

    def return_retiver(self, serach_kwargs: dict):
        retriver = self.vector_storage.as_retriever(
            search_type="similarity",
            search_kwargs=serach_kwargs,
        )
        return retriver

    def format_found_docs(self, docs):
        return "\n\n".join([doc.page_content for doc in docs])

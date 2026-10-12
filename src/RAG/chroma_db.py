from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStore
from langchain_ollama.embeddings import OllamaEmbeddings


def create_vector_store(embedding_model: str, collection_name: str) -> VectorStore:
    """Create and configure a persistent Chroma vector store using Ollama embeddings.

    Args:
        embedding_model (str): Name of the Ollama embedding model used to
            convert documents and queries into vector representations.
        collection_name (str): Name of the Chroma collection used to
            store and retrieve document embeddings.

    Returns:
        VectorStore: Configured Chroma vector store instance with persistent
            local storage.

    Notes:
        Vector data is persisted in the project's vector_storage directory.
        The collection is created if it does not exist or reused if it
        already exists. The embedding model must be available in Ollama.
    """

    storage_dir = str(Path(__file__).parents[2].resolve() / "vector_storage")

    embeddings = OllamaEmbeddings(model=embedding_model)

    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=storage_dir,
    )

    return vector_store

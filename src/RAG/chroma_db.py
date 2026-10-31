from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStore
from langchain_ollama.embeddings import OllamaEmbeddings


def create_vector_store(
    embedding_model: str,
    collection_name: str,
    ollama_url: str,
    host: str | None = None,
    port: int | None = None,
    storage_dir: str | None = None,
) -> VectorStore:
    """Create or connect to a Chroma vector store using Ollama embeddings.

    Supports both a remote Chroma server connection and local persistent
    storage, depending on the provided configuration.

    Args:
        embedding_model (str): Name of the Ollama model used to generate
            embeddings for documents and queries.
        collection_name (str): Name of the Chroma collection to create
            or reuse if it already exists.
        ollama_url (str): Base URL of the Ollama server providing the
            embedding model.
        host (str | None): Hostname or IP address of the Chroma server.
            Defaults to None.
        port (int | None): Port number of the Chroma server.
            Defaults to None.
        storage_dir (str | None): Directory for local persistent storage.
            Defaults to None.

    Returns:
        VectorStore: Configured Chroma vector store instance.

    Notes:
        The embedding model must be available on the Ollama server.
        Existing collections are reused if they already exist.

        For local persistence, pass storage_dir to Chroma using
        the persist_directory parameter.
    """

    embeddings = OllamaEmbeddings(model=embedding_model, base_url=ollama_url)

    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        host=host,
        port=port,
        persist_directory=storage_dir,
    )

    return vector_store

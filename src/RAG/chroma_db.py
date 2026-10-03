from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStore
from langchain_ollama.embeddings import OllamaEmbeddings

storage_dir = str(Path(__file__).parents[2].resolve() / "vector_storage")
# ! Tu mozna dodac model embeddingwoy i inen rzeczy do Pydantic Settigns


def create_vector_store() -> VectorStore:
    embeddings = OllamaEmbeddings(model="embeddinggemma")

    vector_store = Chroma(
        collection_name="AI_chat_bot_collection",
        embedding_function=embeddings,
        persist_directory=storage_dir,
    )

    return vector_store

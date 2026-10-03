from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

storage_dir = str(Path(__file__).parents[2].resolve() / "vector_storage")


def load_and_split_file(file_path: Path):
    loader = PyPDFLoader(file_path=file_path)
    doc = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    doc_split = splitter.split_documents(doc)
    return doc_split


def create_vector_store():
    embeddings = OllamaEmbeddings(model="embeddinggemma")

    vector_store = Chroma(
        collection_name="example_collection",
        embedding_function=embeddings,
        persist_directory=storage_dir,
    )

    return vector_store


def create_vector_store_load_doc(file_path):
    doc_chunks = load_and_split_file(file_path=file_path)
    vector_store = create_vector_store()

    vector_store.add_documents(documents=doc_chunks)
    return vector_store


def rag(file_path, question):
    vector_store = create_vector_store_load_doc(file_path)

    retriver = vector_store.as_retriever(
        search_type="similarity", search_kwargs={"k": 2}
    )

    llm = ChatOllama(model="llama3:8b")

    prompt = ChatPromptTemplate.from_template("""
        Answer the question based only on the following context:

        {context}

        Question: {question}

        Answer:


        Make sure to answer in a concise manner, 
        and if you don't know the answer, just say "I don't know.""")

    def format_docs(docs):
        return "\n\n".join([doc.page_content for doc in docs])

    rag_chain = (
        {
            "context": retriver | format_docs,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    answer = rag_chain.invoke(input=question)
    return answer


answer = rag(
    file_path="storage/1/79cec84a-bd28-49ad-9186-6fdf970a0233_rag_test_document.pdf",
    question="What happens when indexing fails?",
)
print(answer)

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

from deepeval import evaluate
from deepeval.evaluate import AsyncConfig, DisplayConfig
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.models import OllamaModel
from deepeval.test_case import LLMTestCase

from backend.chat_bot.client import ChatBotClient
from backend.configuration.settings import get_settings
from backend.service.chat_service import ChatService
from RAG.chroma_db import create_vector_store
from RAG.document_indexing_seervice import DocumentIndexingService
from RAG.file_vector_repository import FileVectorStorage

#! Setup
TEST_COLLECTION_NAME: str = "test_eval_vector_storage"
test_docs_path: Path = Path(
    "tests/RAG_evals/data/harborline_rag_benchmark_10_pages.pdf"
)
TEST_USR_ID: int = -1

settings = get_settings()
config = {
    "chunk_size": settings.chunk_size,
    "chunk_overlap": settings.chunk_overlap,
    "embedding_model": settings.embedding_model,
    "top_k": settings.test_deepevals_top_k,
}
test_results_path: str = "./evals_results/single/basic/test_results"
config_path: Path = Path("evals_results/single/basic/test_config.json")
data_chunks_path: Path = Path(
    "evals_results/single/basic/test_data_chunks_example.json"
)
single_turn_golden_dataset_path: Path = Path("tests/RAG_evals/single_turn_goldens.json")

# Create directories if they don't exist
config_path.parent.mkdir(parents=True, exist_ok=True)
data_chunks_path.parent.mkdir(parents=True, exist_ok=True)

# ! TESTS
with config_path.open("w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

with tempfile.TemporaryDirectory() as dir_storage_test:

    test_vector_store = create_vector_store(
        embedding_model=settings.embedding_model,
        collection_name=TEST_COLLECTION_NAME,
        storage_dir=dir_storage_test,
    )

    document_index_service = DocumentIndexingService(
        chunk_overlap=settings.chunk_overlap, chunk_size=settings.chunk_size
    )

    chat_client = ChatBotClient()

    file_vector_storage = FileVectorStorage(
        vector_db=test_vector_store,
        file_index_service=document_index_service,
    )

    service = ChatService(
        db=Mock(), chat_bot_client=chat_client, file_vector_storage=file_vector_storage
    )

    model = OllamaModel(
        model=settings.test_deepevals_model, temperature=settings.test_deepevals_temp
    )
    # ! ADD docs to test Vector Storage
    file_vector_storage.add_document(file_path=test_docs_path, user_id=TEST_USR_ID)

    # Save some chunks to examine how chunking is working in the experiment
    data_chunks_example = test_vector_store.get(  # type: ignore
        where={"page": 2},
        include=["documents", "metadatas"],
    )

    with data_chunks_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(data_chunks_example, f, indent=2, ensure_ascii=False)

    # Build RAG chain
    rag_chain = service.build_rag_chain(
        model=settings.test_deepevals_model,
        temperature=settings.test_deepevals_temp,
        top_k=settings.test_deepevals_top_k,
        top_p=settings.test_deepevals_top_p,
        num_ctx=settings.test_deepevals_num_ctx,
        num_predict=settings.test_deepevals_temp_num_predict,
        repeat_penalty=settings.test_deepevals_repeat_penalty,
        is_thinking=settings.test_deepevals_is_thinking,
        user_id=TEST_USR_ID,
    )
    with open(single_turn_golden_dataset_path, "r") as file:
        golden_json_data = json.load(file)

    # ! TESTS
    # Since I mostly use Ollama locally, switch off async to prevent errors.
    tests = []

    metric_context = ContextualRelevancyMetric(
        threshold=0.7, model=model, async_mode=False, include_reason=True
    )
    metric_relevancy = AnswerRelevancyMetric(
        threshold=0.7, model=model, async_mode=False, include_reason=True
    )
    metric_faithfulness = FaithfulnessMetric(
        threshold=0.7, model=model, async_mode=False, include_reason=True
    )
    metric_precision = ContextualPrecisionMetric(
        threshold=0.7, model=model, async_mode=False, include_reason=True
    )

    metric_recall = ContextualRecallMetric(
        threshold=0.7, model=model, async_mode=False, include_reason=True
    )
    for data_input in golden_json_data:
        question: str = data_input["input"]
        expected_output: str = data_input["expected_output"]
        result = rag_chain.invoke({"input": question, "chat_history": []})

        result_answer = result["answer"]
        retrieval_context = [doc.page_content for doc in result["context"]]

        test_case = LLMTestCase(
            input=question,
            actual_output=result_answer,
            retrieval_context=retrieval_context,
            expected_output=expected_output,
        )

        tests.append(test_case)

    evaluate(
        test_cases=tests,
        metrics=[
            metric_context,
            metric_relevancy,
            metric_faithfulness,
            metric_precision,
            metric_recall,
        ],
        async_config=AsyncConfig(run_async=False),
        display_config=DisplayConfig(
            results_folder=test_results_path,
            file_type="html",
            file_output_dir=test_results_path,
        ),
    )

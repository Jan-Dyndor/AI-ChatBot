import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

from deepeval import evaluate
from deepeval.evaluate import AsyncConfig, DisplayConfig
from deepeval.metrics import (
    TurnContextualPrecisionMetric,
    TurnContextualRecallMetric,
    TurnContextualRelevancyMetric,
    TurnFaithfulnessMetric,
)
from deepeval.models import OllamaModel
from deepeval.test_case import ConversationalTestCase, Turn
from langchain_core.messages import AIMessage, HumanMessage

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

config_path = Path("evals_results/multi/basic/test_config.json")
data_chunks_path = Path("evals_results/multi/basic/test_data_chunks_example.json")
multi_turn_golden_dataset_path: Path = Path("tests/RAG_evals/multi_turn_goldens.json")

test_results_path: str = "./evals_results/multi/basic/test_results"
# Create directories if they don't exist
config_path.parent.mkdir(parents=True, exist_ok=True)
data_chunks_path.parent.mkdir(parents=True, exist_ok=True)

with config_path.open("w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

#! TESTS
with tempfile.TemporaryDirectory() as test_temp_dir:

    document_index_service = DocumentIndexingService(
        chunk_overlap=settings.chunk_overlap, chunk_size=settings.chunk_size
    )

    chat_client = ChatBotClient(ollama_url=settings.ollama_url)

    test_vector_store = create_vector_store(
        embedding_model=settings.embedding_model,
        collection_name=TEST_COLLECTION_NAME,
        storage_dir=test_temp_dir,
        ollama_url=settings.ollama_url,
    )

    file_vector_storage = FileVectorStorage(
        vector_db=test_vector_store,
        file_index_service=document_index_service,
    )

    service = ChatService(
        db=Mock(), chat_bot_client=chat_client, file_vector_storage=file_vector_storage
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

    model = OllamaModel(model=settings.test_deepevals_model, temperature=0)

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
    expected_outcomes = {
        "refund_vs_service_credit": "User understands refund deadlines, when the refund timer starts, and how refund deadlines differ from service-credit request deadlines.",
        "chilled_temperature_and_quality_hold": "User understands the difference between temperature alerts and mandatory quality holds, including their thresholds and who can authorize release.",
        "standard_cutoff_and_dispatch_definition": "User understands Standard order cutoffs, next-day processing after a missed cutoff, and what officially counts as dispatch.",
        "stock_variance_followups": "User understands when inventory variances require escalation and can distinguish the absolute-unit threshold from the percentage threshold.",
        "express_service_credit_and_cap": "User understands Express dispatch-credit eligibility, how to calculate credits, the monthly cap, and why carrier delivery delays do not automatically qualify.",
    }

    with open(multi_turn_golden_dataset_path, "r") as file:
        data_json = json.load(file)

    tests_conversational = []
    for topics in data_json:
        chat_history = []
        turns = []
        for question in topics["turns"]:
            turns.append(Turn(role="user", content=question["input"]))

            result = rag_chain.invoke(
                {"input": question["input"], "chat_history": chat_history}
            )
            context = [doc.page_content for doc in result["context"]]

            chat_history.append(HumanMessage(content=question["input"]))
            chat_history.append(AIMessage(content=result["answer"]))

            turns.append(
                Turn(
                    role="assistant",
                    content=result["answer"],
                    retrieval_context=context,
                )
            )

        tests_conversational.append(
            ConversationalTestCase(
                turns=turns, expected_outcome=expected_outcomes[topics["topic"]]
            )
        )

    evaluate(
        test_cases=tests_conversational,
        metrics=[
            TurnFaithfulnessMetric(
                model=model, threshold=0.7, async_mode=True, include_reason=True
            ),
            TurnContextualRelevancyMetric(
                model=model, threshold=0.7, async_mode=True, include_reason=True
            ),
            TurnContextualPrecisionMetric(
                model=model, threshold=0.7, async_mode=True, include_reason=True
            ),
            TurnContextualRecallMetric(
                model=model, threshold=0.7, async_mode=True, include_reason=True
            ),
        ],
        async_config=AsyncConfig(run_async=True, max_concurrent=1),
        display_config=DisplayConfig(
            results_folder=test_results_path,
            file_type="html",
            file_output_dir=test_results_path,
        ),
    )

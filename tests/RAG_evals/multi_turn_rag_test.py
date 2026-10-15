import json
from unittest.mock import Mock

from deepeval import evaluate
from deepeval.evaluate import AsyncConfig
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
settings = get_settings()

document_index_service = DocumentIndexingService(
    chunk_overlap=settings.chunk_overlap, chunk_size=settings.chunk_size
)

chat_client = ChatBotClient()

file_vector_storage = FileVectorStorage(
    vector_db=create_vector_store(
        embedding_model=settings.embedding_model,
        collection_name=settings.collection_name_vector_store,
    ),
    file_index_service=document_index_service,
)

service = ChatService(
    db=Mock(), chat_bot_client=chat_client, file_vector_storage=file_vector_storage
)

model = OllamaModel(model="llama3:8b", temperature=0)

rag_chain = service.build_rag_chain(
    model="llama3:8b",
    temperature=0,
    top_k=40,
    top_p=0.9,
    num_ctx=4096,
    num_predict=300,
    repeat_penalty=1.1,
    is_thinking=False,
    user_id=1,
)
expected_outcomes = {
    "refund_vs_service_credit": "User understands refund deadlines, when the refund timer starts, and how refund deadlines differ from service-credit request deadlines.",
    "chilled_temperature_and_quality_hold": "User understands the difference between temperature alerts and mandatory quality holds, including their thresholds and who can authorize release.",
    "standard_cutoff_and_dispatch_definition": "User understands Standard order cutoffs, next-day processing after a missed cutoff, and what officially counts as dispatch.",
    "stock_variance_followups": "User understands when inventory variances require escalation and can distinguish the absolute-unit threshold from the percentage threshold.",
    "express_service_credit_and_cap": "User understands Express dispatch-credit eligibility, how to calculate credits, the monthly cap, and why carrier delivery delays do not automatically qualify.",
}

with open("tests/RAG_evals/multi_turn_goldens.json", "r") as file:
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
            Turn(role="assistant", content=result["answer"], retrieval_context=context)
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
)

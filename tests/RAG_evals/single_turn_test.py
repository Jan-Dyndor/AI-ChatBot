import json
from unittest.mock import Mock

from deepeval import evaluate
from deepeval.evaluate import AsyncConfig
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

model = OllamaModel(
    model=settings.test_deepevals_model, temperature=settings.test_deepevals_temp
)

rag_chain = service.build_rag_chain(
    model=settings.test_deepevals_model,
    temperature=settings.test_deepevals_temp,
    top_k=settings.test_deepevals_top_k,
    top_p=settings.test_deepevals_top_p,
    num_ctx=settings.test_deepevals_num_ctx,
    num_predict=settings.test_deepevals_temp_num_predict,
    repeat_penalty=settings.test_deepevals_repeat_penalty,
    is_thinking=settings.test_deepevals_is_thinking,
    user_id=settings.test_deepevals_user_id,
)
with open("tests/RAG_evals/single_turn_goldens.json", "r") as file:
    golden_json_data = json.load(file)

# ! Later on figure out how to pass there a PDF without manual upload it to user with ID , just use some test account or what


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
)

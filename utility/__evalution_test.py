from deepeval.metrics import (
    ContextualRecallMetric,
    ContextualPrecisionMetric,
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualRelevancyMetric,
)
from deepeval.test_case import LLMTestCase
from deepeval import evaluate
from deepeval.evaluate.configs import CacheConfig

query = "What is your refund policy?"

actual_output = (
    "We offer a 15-day full refund at no extra cost. Customers are free to roam around"
)

expected_output = "You are eligible for a 30 day refund at an extra cost of $55. The items should not be damaged or used to qualify for a refund."

retrieval_context = [
    "We are loacated in Bangalore, India. You can contact us at contact@company.com",
    "All customers are eligible for a 30 day full refund at an extra cost of $55",
]

test_case = LLMTestCase(
    input=query,
    actual_output=actual_output,
    expected_output=expected_output,
    retrieval_context=retrieval_context,
)

recall_metric = ContextualRecallMetric(
    threshold=0.7, model="gpt-4o", include_reason=True
)
precision_metric = ContextualPrecisionMetric(
    threshold=0.7, model="gpt-4o", include_reason=True
)
faithfulness_metric = FaithfulnessMetric(
    threshold=0.7, model="gpt-4o", include_reason=True
)
answer_relevancy_metric = AnswerRelevancyMetric(
    threshold=0.7, model="gpt-4o", include_reason=True
)
contextual_relevancy_metric = ContextualRelevancyMetric(
    threshold=0.7, model="gpt-4o", include_reason=True
)
evaluate(
    test_cases=[test_case],
    metrics=[
        recall_metric,
        precision_metric,
        faithfulness_metric,
        answer_relevancy_metric,
        contextual_relevancy_metric,
    ],
    cache_config=CacheConfig(write_cache=False, use_cache=False),
)

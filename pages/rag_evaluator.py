import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
from deepeval.metrics import ContextualPrecisionMetric, ContextualRecallMetric
from deepeval.test_case import LLMTestCase
from dotenv import load_dotenv

load_dotenv()

from utility.tools.rag_query_tools import query_rag_documents
from utility.tools.pg_tools import direct_db_access

st.set_page_config(page_title="RAG Evaluator", page_icon=":bar_chart:", layout="wide")

GOLDEN_DATASET_DIR = Path(__file__).resolve().parent.parent / "golden_dataset"
DATASET_FIELDS = {"input", "expected_output", "context"}
RESULTS_KEY = "rag_evaluation_results"
HISTORY_KEY = "rag_evaluation_history"
HISTORY_SELECTION_KEY = "rag_evaluation_history_selection"


def _int_env(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return int(default)


def _load_dataset(payload, source_name):
    try:
        dataset = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"{source_name} is not valid JSON: {exc}") from exc

    if not isinstance(dataset, list) or not dataset:
        raise ValueError("A dataset must be a non-empty JSON array.")

    for index, case in enumerate(dataset, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"Test case {index} must be a JSON object.")
        missing_fields = DATASET_FIELDS - case.keys()
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"Test case {index} is missing: {missing}.")
        if not isinstance(case["input"], str) or not case["input"].strip():
            raise ValueError(f"Test case {index} must have a non-empty input.")
        if (
            not isinstance(case["expected_output"], str)
            or not case["expected_output"].strip()
        ):
            raise ValueError(
                f"Test case {index} must have a non-empty expected_output."
            )
        if not isinstance(case["context"], list) or not all(
            isinstance(context, str) and context.strip() for context in case["context"]
        ):
            raise ValueError(
                f"Test case {index} context must be a list of non-empty strings."
            )

    return dataset


def _parse_retrieval_context(formatted_context):
    if not formatted_context.strip():
        return []

    chunks = re.split(
        r"(?m)^Chunk Score [^\n]*?\(Document: [^\n]*?\): ",
        formatted_context,
    )
    return [chunk.strip() for chunk in chunks[1:] if chunk.strip()]


def _score_metric(metric_class, threshold, model, test_case):
    metric = metric_class(
        threshold=threshold,
        model=model or None,
        include_reason=True,
        async_mode=False,
    )
    score = metric.measure(test_case, _show_indicator=False)
    return {
        "score": score,
        "reason": metric.reason,
        "passed": metric.success,
    }


def _sql_literal(value):
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def _remove_null_characters(value):
    if isinstance(value, str):
        # PostgreSQL JSONB rejects both NUL characters and JSON's escaped NUL.
        return re.sub(r"\\u0000", "", value.replace("\x00", ""), flags=re.IGNORECASE)
    if isinstance(value, list):
        return [_remove_null_characters(item) for item in value]
    if isinstance(value, dict):
        return {
            _remove_null_characters(key): _remove_null_characters(item)
            for key, item in value.items()
        }
    return value


def _load_evaluation_history():
    direct_db_access("CREATE SCHEMA IF NOT EXISTS rag_evaluator")
    direct_db_access("""
        CREATE TABLE IF NOT EXISTS rag_evaluator.evaluation_history (
            evaluation_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL,
            dataset TEXT NOT NULL,
            evaluation JSONB NOT NULL
        )
        """)
    _, rows = direct_db_access("""
        SELECT evaluation_id, created_at, dataset, evaluation
        FROM rag_evaluator.evaluation_history
        ORDER BY created_at DESC
        """)
    return [
        {
            "evaluation_id": evaluation_id,
            "created_at": created_at,
            "dataset": dataset,
            "evaluation": (
                json.loads(evaluation) if isinstance(evaluation, str) else evaluation
            ),
        }
        for evaluation_id, created_at, dataset, evaluation in (rows or [])
    ]


if HISTORY_KEY not in st.session_state:
    try:
        st.session_state[HISTORY_KEY] = _load_evaluation_history()
        st.session_state["rag_evaluation_history_db_available"] = True
    except Exception as exc:
        st.session_state[HISTORY_KEY] = []
        st.session_state["rag_evaluation_history_db_available"] = False
        st.warning(f"Could not load evaluation history from PostgreSQL: {exc}")

with st.sidebar:
    st.subheader("Evaluation history")
    if st.button(
        "Reset to defaults",
        key="reset_evaluation_config",
    ):
        st.session_state[HISTORY_SELECTION_KEY] = None
        st.session_state["rag_evaluator_reset_config"] = True
        st.session_state.pop("rag_evaluator_config_token", None)
    history = st.session_state[HISTORY_KEY]
    if history:
        history_ids = [item["evaluation_id"] for item in history]
        selected_history_id = st.radio(
            "Previous evaluations",
            options=history_ids,
            index=None,
            key=HISTORY_SELECTION_KEY,
            format_func=lambda evaluation_id: (
                next(
                    (
                        f"{item['dataset']} — {item['created_at']:%Y-%m-%d %H:%M}"
                        if isinstance(item["created_at"], datetime)
                        else f"{item['dataset']} — {str(item['created_at'])[:16]}"
                    )
                    for item in history
                    if item["evaluation_id"] == evaluation_id
                )
            ),
        )
    else:
        selected_history_id = None
        st.caption("No saved evaluations yet.")

selected_history_record = next(
    (
        item
        for item in st.session_state[HISTORY_KEY]
        if item["evaluation_id"] == selected_history_id
    ),
    None,
)

st.title("RAG Retrieval Evaluator")
st.write(
    "Evaluate retrieved context against a golden dataset using contextual recall "
    "and precision. Answer generation is intentionally not run."
)

dataset_files = sorted(GOLDEN_DATASET_DIR.glob("*.json"))
dataset_options = [path.name for path in dataset_files]
if selected_history_record:
    st.session_state["rag_evaluator_dataset"] = selected_history_record["dataset"]
elif "rag_evaluator_dataset" not in st.session_state and dataset_options:
    st.session_state["rag_evaluator_dataset"] = dataset_options[0]

selected_dataset = st.selectbox(
    "Golden dataset", dataset_options, key="rag_evaluator_dataset"
)
dataset_source = selected_dataset

dataset_path = GOLDEN_DATASET_DIR / selected_dataset
try:
    dataset_payload = dataset_path.read_bytes()
except OSError as exc:
    st.error(f"Could not read {dataset_path}: {exc}")
    st.stop()

try:
    test_cases = _load_dataset(dataset_payload, selected_dataset)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

active_history_record = selected_history_record
if active_history_record is None and not st.session_state.get(
    "rag_evaluator_reset_config", False
):
    active_history_record = next(
        (
            item
            for item in st.session_state[HISTORY_KEY]
            if item["dataset"] == dataset_source
        ),
        None,
    )

config_token = (
    active_history_record["evaluation_id"] if active_history_record else None,
    dataset_source,
)
if st.session_state.get("rag_evaluator_config_token") != config_token:
    saved_config = active_history_record["evaluation"] if active_history_record else {}
    retrieval_config = saved_config.get("retrieval_config", {})
    metric_thresholds = saved_config.get("metric_thresholds", {})
    saved_case_indices = {
        result["case_number"] - 1
        for result in saved_config.get("results", [])
        if isinstance(result.get("case_number"), int)
        and 1 <= result["case_number"] <= len(test_cases)
    }
    st.session_state["rag_evaluator_cases"] = (
        sorted(saved_case_indices)
        if active_history_record
        else list(range(len(test_cases)))
    )
    st.session_state["rag_evaluator_chunking"] = retrieval_config.get(
        "chunked_data_type", "fixed"
    )
    st.session_state["rag_evaluator_rerank"] = retrieval_config.get(
        "rerank_flag", False
    )
    st.session_state["rag_evaluator_keyword"] = retrieval_config.get(
        "keyword_search_flag", True
    )
    st.session_state["rag_evaluator_min_chunk"] = retrieval_config.get(
        "CHUNK_SIZE_FILTER_THRESHOLD",
        max(0, _int_env("CHUNK_SIZE_FILTER_THRESHOLD", 500)),
    )
    st.session_state["rag_evaluator_vector_count"] = retrieval_config.get(
        "VECTOR_SEARCH_CHUNK_THRESHOLD",
        min(500, max(1, _int_env("VECTOR_SEARCH_CHUNK_THRESHOLD", 13))),
    )
    st.session_state["rag_evaluator_keyword_count"] = retrieval_config.get(
        "KEYWORD_SEARCH_CHUNK_THRESHOLD",
        min(500, max(1, _int_env("KEYWORD_SEARCH_CHUNK_THRESHOLD", 10))),
    )
    st.session_state["rag_evaluator_rerank_top_k"] = retrieval_config.get(
        "RERANK_TOP_K", min(100, max(1, _int_env("RERANK_TOP_K", 3)))
    )
    st.session_state["rag_evaluator_recall"] = (
        metric_thresholds.get("recall") is not None if active_history_record else True
    )
    st.session_state["rag_evaluator_precision"] = (
        metric_thresholds.get("precision") is not None
        if active_history_record
        else True
    )
    st.session_state["rag_evaluator_recall_threshold"] = metric_thresholds.get("recall")
    if st.session_state["rag_evaluator_recall_threshold"] is None:
        st.session_state["rag_evaluator_recall_threshold"] = 0.7
    st.session_state["rag_evaluator_precision_threshold"] = metric_thresholds.get(
        "precision"
    )
    if st.session_state["rag_evaluator_precision_threshold"] is None:
        st.session_state["rag_evaluator_precision_threshold"] = 0.7
    st.session_state["rag_evaluator_config_token"] = config_token
    st.session_state.pop("rag_evaluator_reset_config", None)

selected_case_indices = st.multiselect(
    "Test cases to evaluate",
    options=list(range(len(test_cases))),
    default=list(range(len(test_cases))),
    key="rag_evaluator_cases",
    format_func=lambda index: (
        f"{index + 1}. {test_cases[index]['input'].strip()[:100]}"
    ),
)
if not selected_case_indices:
    st.warning("Select at least one test case.")

st.subheader("Retriever configuration")
settings_left, settings_right = st.columns(2)
with settings_left:
    chunked_data_type = st.selectbox(
        "Chunking strategy", ["fixed", "recursive"], key="rag_evaluator_chunking"
    )
    rerank_flag = st.checkbox("Rerank retrieved chunks", key="rag_evaluator_rerank")
    keyword_search_flag = st.checkbox(
        "Include keyword search", key="rag_evaluator_keyword"
    )
    chunk_size_threshold = st.number_input(
        "Minimum chunk length",
        min_value=0,
        value=max(0, _int_env("CHUNK_SIZE_FILTER_THRESHOLD", 500)),
        step=50,
        help="Chunks shorter than this value are excluded by the retriever.",
        key="rag_evaluator_min_chunk",
    )
with settings_right:
    vector_search_threshold = st.number_input(
        "Vector search candidates",
        min_value=1,
        max_value=500,
        value=min(500, max(1, _int_env("VECTOR_SEARCH_CHUNK_THRESHOLD", 13))),
        step=1,
        key="rag_evaluator_vector_count",
    )
    keyword_search_threshold = st.number_input(
        "Keyword search results",
        min_value=1,
        max_value=500,
        value=min(500, max(1, _int_env("KEYWORD_SEARCH_CHUNK_THRESHOLD", 10))),
        step=1,
        disabled=not keyword_search_flag,
        key="rag_evaluator_keyword_count",
    )
    rerank_top_k = st.number_input(
        "Reranked top-k",
        min_value=1,
        max_value=100,
        value=min(100, max(1, _int_env("RERANK_TOP_K", 3))),
        step=1,
        disabled=not rerank_flag,
        key="rag_evaluator_rerank_top_k",
    )

st.subheader("Evaluation metrics")
metric_left, metric_right = st.columns(2)
with metric_left:
    evaluate_recall = st.checkbox("Contextual recall", key="rag_evaluator_recall")
    recall_threshold = st.slider(
        "Recall pass threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.05,
        key="rag_evaluator_recall_threshold",
    )
with metric_right:
    evaluate_precision = st.checkbox(
        "Contextual precision", key="rag_evaluator_precision"
    )
    precision_threshold = st.slider(
        "Precision pass threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.05,
        key="rag_evaluator_precision_threshold",
    )

evaluation_model = os.getenv("OPENAI_EVAL_MODEL", "")

if not evaluate_recall and not evaluate_precision:
    st.warning("Select at least one evaluation metric.")

run_evaluation = st.button(
    "Run retrieval evaluation",
    type="primary",
    disabled=(not selected_case_indices or not (evaluate_recall or evaluate_precision)),
)

if run_evaluation:
    results = []
    progress = st.progress(0)
    status = st.empty()
    for completed, case_index in enumerate(selected_case_indices, start=1):
        case = test_cases[case_index]
        status.info(
            f"Retrieving and scoring test case {completed}/{len(selected_case_indices)}"
        )
        try:
            formatted_retrieval = query_rag_documents(
                user_input=case["input"],
                chunked_data_type=chunked_data_type,
                rerank_flag=rerank_flag,
                keyword_search_flag=keyword_search_flag,
                CHUNK_SIZE_FILTER_THRESHOLD=int(chunk_size_threshold),
                VECTOR_SEARCH_CHUNK_THRESHOLD=int(vector_search_threshold),
                KEYWORD_SEARCH_CHUNK_THRESHOLD=int(keyword_search_threshold),
                RERANK_TOP_K=int(rerank_top_k),
            )
            retrieval_context = _parse_retrieval_context(formatted_retrieval)
            result = {
                "case_number": case_index + 1,
                "input": case["input"],
                "expected_output": case["expected_output"],
                "source_file": case.get("source_file", ""),
                "retrieval_context": retrieval_context,
                "retrieval_count": len(retrieval_context),
                "recall": None,
                "precision": None,
                "error": None,
            }

            if not retrieval_context:
                result["error"] = (
                    "The retriever returned no chunks; metrics were not scored."
                )
            else:
                metric_test_case = LLMTestCase(
                    input=case["input"],
                    expected_output=case["expected_output"],
                    retrieval_context=retrieval_context,
                )
                metric_errors = []
                if evaluate_recall:
                    try:
                        result["recall"] = _score_metric(
                            ContextualRecallMetric,
                            recall_threshold,
                            evaluation_model,
                            metric_test_case,
                        )
                    except Exception as exc:
                        metric_errors.append(f"Recall: {exc}")
                if evaluate_precision:
                    try:
                        result["precision"] = _score_metric(
                            ContextualPrecisionMetric,
                            precision_threshold,
                            evaluation_model,
                            metric_test_case,
                        )
                    except Exception as exc:
                        metric_errors.append(f"Precision: {exc}")
                if metric_errors:
                    result["error"] = "; ".join(metric_errors)

            results.append(result)
        except Exception as exc:
            results.append(
                {
                    "case_number": case_index + 1,
                    "input": case["input"],
                    "expected_output": case["expected_output"],
                    "source_file": case.get("source_file", ""),
                    "retrieval_context": [],
                    "retrieval_count": 0,
                    "recall": None,
                    "precision": None,
                    "error": f"Retrieval failed: {exc}",
                }
            )
        progress.progress(completed / len(selected_case_indices))

    st.session_state[RESULTS_KEY] = {
        "dataset": dataset_source,
        "results": results,
        "retrieval_config": {
            "chunked_data_type": chunked_data_type,
            "rerank_flag": rerank_flag,
            "keyword_search_flag": keyword_search_flag,
            "CHUNK_SIZE_FILTER_THRESHOLD": int(chunk_size_threshold),
            "VECTOR_SEARCH_CHUNK_THRESHOLD": int(vector_search_threshold),
            "KEYWORD_SEARCH_CHUNK_THRESHOLD": int(keyword_search_threshold),
            "RERANK_TOP_K": int(rerank_top_k),
        },
        "metric_thresholds": {
            "recall": recall_threshold if evaluate_recall else None,
            "precision": precision_threshold if evaluate_precision else None,
        },
        "evaluation_model": evaluation_model or None,
    }
    st.session_state[RESULTS_KEY] = _remove_null_characters(
        st.session_state[RESULTS_KEY]
    )
    evaluation_id = str(uuid.uuid4())
    created_at = datetime.now().astimezone()
    evaluation_record = {
        "evaluation_id": evaluation_id,
        "created_at": created_at.isoformat(),
        "dataset": dataset_source,
        "evaluation": st.session_state[RESULTS_KEY],
    }
    try:
        direct_db_access(f"""
            INSERT INTO rag_evaluator.evaluation_history
                (evaluation_id, created_at, dataset, evaluation)
            VALUES (
                {_sql_literal(evaluation_id)},
                {_sql_literal(created_at.isoformat())}::timestamptz,
                {_sql_literal(dataset_source)},
                {_sql_literal(json.dumps(st.session_state[RESULTS_KEY], ensure_ascii=False))}::jsonb
            )
            """)
        st.session_state[HISTORY_KEY].insert(0, evaluation_record)
        st.session_state["rag_evaluation_history_db_available"] = True
        st.session_state[HISTORY_SELECTION_KEY] = evaluation_id
    except Exception as exc:
        st.warning(f"Evaluation completed, but could not save it to PostgreSQL: {exc}")
    status.empty()

saved_evaluation = None
if selected_history_id:
    selected_record = next(
        (
            item
            for item in st.session_state[HISTORY_KEY]
            if item["evaluation_id"] == selected_history_id
        ),
        None,
    )
    if selected_record:
        saved_evaluation = selected_record["evaluation"]
else:
    latest_dataset_evaluation = next(
        (
            item
            for item in st.session_state[HISTORY_KEY]
            if item["dataset"] == dataset_source
        ),
        None,
    )
    if latest_dataset_evaluation:
        saved_evaluation = latest_dataset_evaluation["evaluation"]
    else:
        saved_evaluation = st.session_state.get(RESULTS_KEY)

if saved_evaluation:
    results = saved_evaluation["results"]
    st.divider()
    st.subheader("Evaluation results")
    summary_columns = st.columns(2)
    for metric_index, metric_name in enumerate(("recall", "precision")):
        scored = [
            result[metric_name]["score"]
            for result in results
            if result[metric_name] is not None
        ]
        if scored:
            summary_columns[metric_index].metric(
                f"Average contextual {metric_name}",
                f"{sum(scored) / len(scored):.2f}",
            )

    table_rows = []
    for result in results:
        table_rows.append(
            {
                "Case": result["case_number"],
                "Question": result["input"],
                "Retrieved chunks": result["retrieval_count"],
                "Recall": (
                    f"{result['recall']['score']:.2f}"
                    if result["recall"] is not None
                    else "—"
                ),
                "Precision": (
                    f"{result['precision']['score']:.2f}"
                    if result["precision"] is not None
                    else "—"
                ),
                "Status": result["error"] or "Scored",
            }
        )
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    for result in results:
        with st.expander(f"Case {result['case_number']}: {result['input']}"):
            st.markdown("**Expected answer (used as the retrieval reference)**")
            st.write(result["expected_output"])
            st.markdown("**Retrieved chunks**")
            if result["retrieval_context"]:
                for chunk_number, chunk in enumerate(
                    result["retrieval_context"], start=1
                ):
                    st.markdown(f"Chunk {chunk_number}")
                    st.write(chunk)
            else:
                st.info("No chunks were returned.")
            for metric_name in ("recall", "precision"):
                metric_result = result[metric_name]
                if metric_result is not None:
                    st.markdown(
                        f"**Contextual {metric_name}: {metric_result['score']:.2f} "
                        f"({'passed' if metric_result['passed'] else 'below threshold'})**"
                    )
                    st.write(metric_result["reason"])
            if result["error"]:
                st.error(result["error"])

    st.download_button(
        "Download evaluation results (JSON)",
        data=json.dumps(saved_evaluation, indent=2, ensure_ascii=False),
        file_name="rag-evaluation-results.json",
        mime="application/json",
    )

import json
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

from utility.database.history import load_history_records, save_history_record
from utility.database.json_utilities import remove_null_characters
from utility.evaluation.course_reviews_evaluation import (
    NOUL_SCORE_THRESHOLD,
    course_reviews_eval,
)
from utility.ingestion.course_reviews import (
    list_ingested_courses,
    load_review_metadata,
)
from utility.ui.page_utilities import (
    format_history_timestamp,
    render_history_selector,
)

st.set_page_config(
    page_title="Course Reviews Deep Dive", page_icon=":mag:", layout="wide"
)

EVALUATION_SCHEMA = "course_reviews_evaluation"
HISTORY_KEY = "course_reviews_evaluation_history"
HISTORY_SELECTION_KEY = "course_reviews_evaluation_history_selection"
LATEST_EVALUATION_KEY = "course_reviews_latest_evaluation"
CLEAR_RESULTS_KEY = "reviews_deepdive_results_cleared"

CRITERION_LABELS = {
    "curriculum": "Curriculum",
    "about_instructor": "Instructor credibility",
    "hands_on_work": "Hands-on work",
    "mentorship_support": "Mentorship and support",
    "career_outcome": "Career outcomes",
    "learning_experience": "Learning experience",
    "cost_price_worth": "Cost and value",
    "flexibility": "Flexibility and schedule",
    "industry_relevance": "Industry relevance",
}


def _build_evaluation(course, results):
    criteria = list(CRITERION_LABELS)
    criteria.extend(
        criterion
        for criterion in results.columns
        if criterion not in {"review_id", "review", *criteria}
    )
    criterion_summaries = {}
    all_scores = []
    for criterion in criteria:
        scores = pd.to_numeric(
            results[criterion] if criterion in results else pd.Series(dtype=float),
            errors="coerce",
        ).dropna()
        criterion_summaries[criterion] = {
            "label": CRITERION_LABELS.get(
                criterion, criterion.replace("_", " ").title()
            ),
            "average_score": float(scores.mean()) if not scores.empty else None,
            "review_count": int(scores.size),
        }
        all_scores.extend(float(score) for score in scores)

    review_rows = json.loads(results.to_json(orient="records", force_ascii=False))
    return remove_null_characters(
        {
            "course_id": course["id"],
            "course_name": course["name"],
            "course_link": course["link"],
            "created_at": datetime.now().astimezone().isoformat(),
            "noul_score_threshold": NOUL_SCORE_THRESHOLD,
            "overall_score": (
                sum(all_scores) / len(all_scores) if all_scores else None
            ),
            "reviews_evaluated": int(len(results)),
            "criteria": criterion_summaries,
            "reviews": review_rows,
        }
    )


def _load_evaluation_history():
    return load_history_records(
        EVALUATION_SCHEMA,
        "evaluation_history",
        {
            "evaluation_id": "TEXT",
            "created_at": "TIMESTAMPTZ",
            "course_id": "TEXT",
            "course_name": "TEXT",
            "course_link": "TEXT",
            "evaluation": "JSONB",
        },
        order_by="created_at",
        primary_key="evaluation_id",
    )


def _save_evaluation(evaluation_id, evaluation):
    save_history_record(
        EVALUATION_SCHEMA,
        "evaluation_history",
        {
            "evaluation_id": "TEXT",
            "created_at": "TIMESTAMPTZ",
            "course_id": "TEXT",
            "course_name": "TEXT",
            "course_link": "TEXT",
            "evaluation": "JSONB",
        },
        {
            "evaluation_id": evaluation_id,
            "created_at": evaluation["created_at"],
            "course_id": evaluation["course_id"],
            "course_name": evaluation["course_name"],
            "course_link": evaluation["course_link"],
            "evaluation": evaluation,
        },
        primary_key="evaluation_id",
    )


def _history_label(record):
    timestamp = format_history_timestamp(record["created_at"])
    return f"{record['course_name']} — {timestamp}"


first_page_load = CLEAR_RESULTS_KEY not in st.session_state
if first_page_load:
    st.session_state[CLEAR_RESULTS_KEY] = True

if HISTORY_KEY not in st.session_state:
    try:
        st.session_state[HISTORY_KEY] = _load_evaluation_history()
        st.session_state["course_reviews_history_db_available"] = True
    except Exception as exc:
        st.session_state[HISTORY_KEY] = []
        st.session_state["course_reviews_history_db_available"] = False
        st.warning(f"Could not load evaluation history from PostgreSQL: {exc}")

with st.sidebar:
    st.subheader("Evaluation history")
    if st.button("Clear results", key="reviews_deepdive_clear"):
        st.session_state.pop(LATEST_EVALUATION_KEY, None)
        st.session_state.pop("reviews_deepdive_selected_criterion", None)
        st.session_state[HISTORY_SELECTION_KEY] = None
        st.session_state[CLEAR_RESULTS_KEY] = True
        st.session_state["reviews_deepdive_history_course_selection"] = None
        st.session_state["reviews_deepdive_course"] = None
        st.rerun()

    history = st.session_state[HISTORY_KEY]
    if history:
        selected_history_id = render_history_selector(
            history,
            HISTORY_SELECTION_KEY,
            "Previous evaluations",
            "No saved evaluations yet.",
            item_id_key="evaluation_id",
            format_func=_history_label,
            reverse=False,
        )
    else:
        selected_history_id = None
        st.caption("No saved evaluations yet.")

selected_history_record = next(
    (
        record
        for record in st.session_state[HISTORY_KEY]
        if record["evaluation_id"] == selected_history_id
    ),
    None,
)
if selected_history_record and not first_page_load:
    st.session_state[CLEAR_RESULTS_KEY] = False

st.title("Course Reviews Deep Dive")
st.write(
    "Evaluate course reviews across key criteria, compare satisfaction scores, "
    "and inspect the reviews contributing to each score."
)

try:
    courses = list_ingested_courses(require_reviews=True)
except Exception as exc:
    st.error(f"Could not load courses with ingested reviews: {exc}")
    courses = []

courses_by_id = {course["id"]: course for course in courses}
new_evaluation_record = None

if (
    selected_history_record
    and selected_history_record["course_id"] in courses_by_id
    and selected_history_id
    != st.session_state.get("reviews_deepdive_history_course_selection")
):
    st.session_state["reviews_deepdive_course"] = selected_history_record["course_id"]
    st.session_state["reviews_deepdive_history_course_selection"] = selected_history_id
elif selected_history_id is None:
    st.session_state["reviews_deepdive_history_course_selection"] = None

if courses:
    course_options = list(courses_by_id)
    if "reviews_deepdive_course" not in st.session_state:
        st.session_state["reviews_deepdive_course"] = None

    selected_course_id = st.selectbox(
        "Select a course",
        options=course_options,
        index=None,
        placeholder="Choose a course",
        format_func=lambda course_id: (
            f"{courses_by_id[course_id]['name']} "
            f"({courses_by_id[course_id]['review_count']} reviews)"
        ),
        key="reviews_deepdive_course",
    )
    selected_course = courses_by_id.get(selected_course_id)

    if selected_course:
        with st.expander("Course details"):
            st.write(f"**Course:** {selected_course['name']}")
            st.write(f"**Course link:** {selected_course['link']}")
            st.write(f"**Reviews:** {selected_course['review_count']}")

    if selected_course and st.button(
        "Start analysis", type="primary", key="reviews_deepdive_start"
    ):
        st.session_state[CLEAR_RESULTS_KEY] = False
        try:
            with st.spinner("Evaluating course reviews..."):
                results = course_reviews_eval(selected_course_id)
                evaluation = _build_evaluation(selected_course, results)
            evaluation_id = str(uuid.uuid4())
            new_evaluation_record = {
                "evaluation_id": evaluation_id,
                "created_at": evaluation["created_at"],
                "course_id": selected_course["id"],
                "course_name": selected_course["name"],
                "course_link": selected_course["link"],
                "evaluation": evaluation,
            }
            st.session_state[LATEST_EVALUATION_KEY] = new_evaluation_record
            st.session_state[HISTORY_KEY].insert(0, new_evaluation_record)
            try:
                _save_evaluation(evaluation_id, evaluation)
                st.session_state["course_reviews_history_db_available"] = True
            except Exception as exc:
                st.error(
                    "Evaluation completed, but could not save it to PostgreSQL: "
                    f"{exc}"
                )
            st.rerun()
        except Exception as exc:
            st.error(f"Could not evaluate course reviews: {exc}")

if new_evaluation_record:
    display_record = new_evaluation_record
elif selected_history_record:
    display_record = selected_history_record
else:
    latest_session_record = st.session_state.get(LATEST_EVALUATION_KEY)
    if (
        latest_session_record
        and courses
        and latest_session_record["course_id"] == selected_course_id
    ):
        display_record = latest_session_record
    else:
        display_record = None

if st.session_state.get(CLEAR_RESULTS_KEY):
    display_record = None

if display_record:
    evaluation = display_record["evaluation"]
    st.subheader(f"Analysis results — {display_record['course_name']}")
    st.caption(f"Evaluated: {_history_label(display_record).split(' — ', 1)[-1]}")

    overall_score = evaluation["overall_score"]
    overall_text = f"{overall_score:.2f} / 5" if overall_score is not None else "N/A"
    summary_column, review_count_column = st.columns(2)
    with summary_column:
        st.metric(
            "Overall satisfaction score",
            overall_text,
            help="Mean numeric rubric score across all matched criteria. The SDK rubric is scored from 0 to 5.",
        )
    with review_count_column:
        st.metric("Reviews evaluated", evaluation["reviews_evaluated"])

    saved_criteria = evaluation.get("criteria") or {}
    criteria = {
        criterion: {
            "label": label,
            "average_score": None,
            "review_count": 0,
            **saved_criteria.get(criterion, {}),
        }
        for criterion, label in CRITERION_LABELS.items()
    }
    criteria.update(
        {
            criterion: summary
            for criterion, summary in saved_criteria.items()
            if criterion not in criteria
        }
    )
    if not criteria:
        st.info("No reviews matched the evaluation criteria.")
    else:
        st.write("Select a criterion to see its matching reviews.")
        criterion_columns = st.columns(3)
        for index, (criterion, summary) in enumerate(criteria.items()):
            average = summary["average_score"]
            score_text = f"{average:.2f} / 5" if average is not None else "N/A"
            with criterion_columns[index % len(criterion_columns)]:
                with st.container(border=True):
                    st.metric(
                        summary["label"],
                        score_text,
                        help="Mean numeric rubric score for reviews mentioning this criterion, on a 0-5 scale.",
                    )
                    st.caption(
                        f"{summary['review_count']} reviews mention this criterion"
                    )
                    if st.button(
                        "View reviews",
                        key=(
                            f"reviews_deepdive_criterion_"
                            f"{display_record['evaluation_id']}_{criterion}"
                        ),
                        use_container_width=True,
                    ):
                        st.session_state["reviews_deepdive_selected_criterion"] = (
                            display_record["evaluation_id"],
                            criterion,
                        )

        selected_criterion = st.session_state.get("reviews_deepdive_selected_criterion")
        if (
            selected_criterion
            and selected_criterion[0] == display_record["evaluation_id"]
            and selected_criterion[1] in criteria
        ):
            criterion = selected_criterion[1]
            st.subheader(f"Reviews for {criteria[criterion]['label']}")
            criterion_reviews = [
                review
                for review in evaluation["reviews"]
                if review.get(criterion) is not None
            ]
            try:
                review_metadata = load_review_metadata(
                    (review.get("review_id") for review in criterion_reviews),
                    course_id=evaluation["course_id"],
                )
            except Exception as exc:
                review_metadata = {}
                st.warning(
                    f"Could not load reviewer names and dates from PostgreSQL: {exc}"
                )

            matching_reviews = [
                {
                    "Date": review_metadata.get(str(review.get("review_id")), {}).get(
                        "date"
                    ),
                    "Person": review_metadata.get(str(review.get("review_id")), {}).get(
                        "person"
                    ),
                    "Review": review.get("review"),
                    "Satisfaction score (0-5)": review.get(criterion),
                }
                for review in criterion_reviews
            ]
            if matching_reviews:
                reviews_frame = pd.DataFrame(matching_reviews)
                reviews_frame["_sort_date"] = pd.to_datetime(
                    reviews_frame["Date"], errors="coerce", utc=True
                )
                reviews_frame = reviews_frame.sort_values(
                    "_sort_date", na_position="last"
                ).drop(columns="_sort_date")
                st.dataframe(
                    reviews_frame,
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No reviews matched this criterion.")
elif not courses and not selected_history_record:
    if st.session_state[HISTORY_KEY]:
        st.info(
            "No courses with ingested reviews are available. Select a saved "
            "evaluation from the history sidebar to review previous results."
        )
    else:
        st.info(
            "No courses with ingested reviews or saved evaluations are available yet."
        )

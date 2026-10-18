from typesafe_sdk import TypeSafeClient, Noul, Score
from dotenv import load_dotenv
from utility.tools.pg_tools import direct_db_access
from utility.database.sql_utilities import sql_literal
import pandas as pd
import os

load_dotenv()

client = TypeSafeClient()
NOUL_SCORE_THRESHOLD = float(os.environ.get("NOUL_SCORE_THRESHOLD"))


def course_reviews_eval(course_id, NOUL_SCORE_THRESHOLD=NOUL_SCORE_THRESHOLD):
    retuned_data = direct_db_access(
        f"select review, review_id from reviews.course_reviews where course_id={sql_literal(course_id)}"
    )

    reviews_flatted = [i[0] for i in retuned_data[1]]

    questions = {
        "curriculum_mentioned": Noul(
            instructions="Does the review mentions about the course curriculum?"
        ),
        "about_instructor_mentioned": Noul(
            instructions="Does the review mentions about the course instructor/trainer and it's credibility?"
        ),
        "hands_on_work_mentioned": Noul(
            instructions="Does the review mentions about the hands on and practial work in course?"
        ),
        "mentorship_support_mentioned": Noul(
            instructions="Does the review mentions about the mentorship and support provided in the course?"
        ),
        "career_outcome_mentioned": Noul(
            instructions="Does the review mentions about the carrer outcomes from course?"
        ),
        "learning_experience_mentioned": Noul(
            instructions="Does the review mentions about the learning experience in the course?"
        ),
        "cost_price_worth_mentioned": Noul(
            instructions="Does the review mentions about the cost, investment or quantative outcomes from the course?"
        ),
        "flexibility_mentioned": Noul(
            instructions="Does the review mentions about the flexiility and schedules in the course?"
        ),
        "industry_relevance_mentioned": Noul(
            instructions="Does the review mentions about industry relevance of the course?"
        ),
    }

    satisfaction_levels = [
        "Very dissatisfied",
        "Dissatisfied",
        "Neither satisfied nor dissatisfied, or balanced mixed feedback",
        "Satisfied",
        "Very satisfied",
        "Exceptional / beyond expectations",
    ]

    reviews_question_answered = []
    for review in reviews_flatted:
        state = {"query": review}
        response = client.system_one(state=state, questions=questions)
        reviews_question_answered.append((review, response.answers))

    review_selected_per_review = {}
    for review_with_answer in reviews_question_answered:
        for question, answer in review_with_answer[1].items():
            if answer.noul > NOUL_SCORE_THRESHOLD:
                if question not in review_selected_per_review.keys():
                    review_selected_per_review[question] = [review_with_answer[0]]
                else:
                    review_selected_per_review[question].append(review_with_answer[0])

    selected_review_scoring = {}

    for question, selected_reviews in review_selected_per_review.items():
        selected_review_scoring[question] = {"reviews": [], "scores": []}
        question_for_scoring = {
            f"{question}_score": Score(
                instructions=f"with respect to {question}, the review lies under which category?",
                criteria=satisfaction_levels,
            )
        }
        for review in selected_reviews:
            response = client.system_one(state=review, questions=question_for_scoring)
            selected_review_scoring[question]["reviews"].append(review)
            selected_review_scoring[question]["scores"].append(response.answers)

    df = pd.DataFrame(
        {
            "review_id": [i[1] for i in retuned_data[1]],
            "review": [i[0] for i in retuned_data[1]],
        }
    )

    for question in questions:
        df[question] = pd.Series(index=df.index, dtype=object)

    for aspect, block in selected_review_scoring.items():
        score_map = {
            review: score_dict[f"{aspect}_score"].score
            for review, score_dict in zip(block["reviews"], block["scores"])
        }
        df[aspect] = df["review"].map(score_map)

    df = df.rename(columns=lambda c: c.replace("_mentioned", ""))
    return df

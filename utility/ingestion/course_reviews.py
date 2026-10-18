from utility.database.sql_utilities import sql_literal
from utility.tools.pg_tools import direct_db_access


def list_ingested_courses(require_reviews=False):
    """List courses stored in the reviews schema with their ingested review counts."""
    _, table_rows = direct_db_access("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'reviews'
          AND table_name IN ('course_reviews_master', 'course_reviews')
        """)
    existing_tables = {row[0] for row in table_rows}
    if "course_reviews_master" not in existing_tables:
        return []

    if "course_reviews" not in existing_tables:
        if require_reviews:
            return []
        _, rows = direct_db_access("""
            SELECT unique_id, course_name, course_link, 0
            FROM reviews.course_reviews_master
            ORDER BY course_name, course_link
            """)
    else:
        join_type = "INNER JOIN" if require_reviews else "LEFT JOIN"
        _, rows = direct_db_access(f"""
            SELECT master.unique_id, master.course_name, master.course_link,
                   COUNT(reviews.review_id) AS review_count
            FROM reviews.course_reviews_master AS master
            {join_type} reviews.course_reviews AS reviews
              ON reviews.course_id = master.unique_id
            GROUP BY master.unique_id, master.course_name, master.course_link
            ORDER BY master.course_name, master.course_link
            """)

    return [
        {"id": course_id, "name": name, "link": link, "review_count": count}
        for course_id, name, link, count in (rows or [])
    ]


def load_review_metadata(review_ids, course_id=None):
    """Load reviewer names and dates for a sequence of stored review IDs."""
    review_ids = list(
        dict.fromkeys(
            str(review_id) for review_id in review_ids if review_id is not None
        )
    )
    if not review_ids:
        return {}

    requested_reviews = ", ".join(
        f"({sql_literal(review_id)})" for review_id in review_ids
    )
    course_filter = (
        f"AND source.course_id = {sql_literal(course_id)}"
        if course_id is not None
        else ""
    )
    _, rows = direct_db_access(f"""
        WITH requested_reviews(review_id) AS (VALUES {requested_reviews})
        SELECT requested_reviews.review_id, source.name, source.review_date
        FROM requested_reviews
        LEFT JOIN reviews.course_reviews AS source
          ON source.review_id::text = requested_reviews.review_id
          {course_filter}
        """)
    return {
        str(review_id): {"person": person, "date": review_date}
        for review_id, person, review_date in (rows or [])
    }

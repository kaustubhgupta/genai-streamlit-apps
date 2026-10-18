#!/usr/bin/env python3
"""
Scrape reviews for a NamasteSQL course through the `scrape_reviews(link)` function.

The course page renders the first batch of reviews in the HTML and loads the
rest through a "Load More" button. This script drives a headless browser
(Playwright), clicks "Load More" until every review is on the page, then
parses the reviews and stores them in PostgreSQL.

Setup:
    pip install playwright beautifulsoup4
    playwright install chromium

"""

import json
import hashlib
import re
import uuid
from datetime import datetime

from bs4 import BeautifulSoup

DEFAULT_URL = (
    "https://www.namastesql.com/course-detail/analytics-engineering-bootcamp-self-paced"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Review dates look like "-31 March, 2026" (day, month name, year).
DATE_RE = re.compile(r"^\s*-?\s*(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})\s*$")
TOTAL_RE = re.compile(r"\((\d+)\s+reviews?\)", re.I)
NOISE = {"show more", "show less", "load more", "load  more"}
HEADINGS = ["h1", "h2", "h3", "h4", "h5", "h6"]
REVIEW_SCHEMA = "reviews"


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def to_iso(day, month, year):
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(f"{day} {month} {year}", fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def expected_total(html):
    """Read the '4.9 (87 reviews)' summary from the page, if present."""
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    m = TOTAL_RE.search(text)
    return int(m.group(1)) if m else None


def parse_reviews(html):
    """
    Structure-based parsing, so it does not depend on CSS class names:
      * every review has a date text node like '-31 March, 2026'
      * the review card is the largest ancestor that contains exactly one date
      * name  = first heading in the card
      * review text = everything else in the card
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    def date_count(node):
        return len(node.find_all(string=DATE_RE))

    reviews, seen = [], set()
    for date_node in soup.find_all(string=DATE_RE):
        card = date_node.parent
        while (
            card.parent is not None
            and card.parent.name not in ("body", "html", "[document]")
            and date_count(card.parent) == 1
        ):
            card = card.parent

        heading = card.find(HEADINGS)
        name = heading.get_text(" ", strip=True) if heading else ""
        date_raw = date_node.strip().lstrip("-").strip()
        m = DATE_RE.match(date_node)
        iso = to_iso(*m.groups()) if m else ""

        parts = []
        for s in card.stripped_strings:
            if s == name or s == date_node.strip() or s.lower() in NOISE:
                continue
            parts.append(s)
        text = "\n".join(parts).strip()

        key = (name, date_raw, text)
        if key in seen or not (name or text):
            continue
        seen.add(key)
        reviews.append(
            {"name": name, "date": iso, "date_raw": date_raw, "review": text}
        )
    return reviews


def course_name_from_html(html, link):
    """Extract the course's display name, falling back to its URL."""
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    if heading and heading.get_text(" ", strip=True):
        return heading.get_text(" ", strip=True)
    title = soup.find("meta", property="og:title")
    if title and title.get("content", "").strip():
        return title["content"].strip()
    if soup.title and soup.title.get_text(" ", strip=True):
        return soup.title.get_text(" ", strip=True)
    return link


# --------------------------------------------------------------------------- #
# Browser automation
# --------------------------------------------------------------------------- #
def scrape(url, headed=False, max_clicks=100, delay_ms=1500):
    # Imported lazily so --from-html works without Playwright installed.
    from playwright.sync_api import TimeoutError as PWTimeout
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        page.goto(url, wait_until="networkidle", timeout=90_000)

        # Reviews sit behind an "Overview / Curriculum / Reviews" tab strip.
        # Click the tab so the Load More button becomes visible.
        try:
            page.get_by_text("Reviews", exact=True).first.click(timeout=5_000)
            page.wait_for_timeout(500)
        except PWTimeout:
            pass

        total = expected_total(page.content())
        load_more = page.get_by_text(re.compile(r"^\s*Load\s*More\s*$", re.I))
        last_count = len(parse_reviews(page.content()))

        stagnant = 0
        for _ in range(1, max_clicks + 1):
            if total and last_count >= total:
                break
            btn = load_more.first
            if btn.count() == 0 or not btn.is_visible():
                break

            btn.scroll_into_view_if_needed()
            btn.click()
            try:
                page.wait_for_load_state("networkidle", timeout=15_000)
            except PWTimeout:
                pass
            page.wait_for_timeout(delay_ms)

            count = len(parse_reviews(page.content()))
            if count == last_count:
                stagnant += 1
                if stagnant >= 3:
                    break
            else:
                stagnant = 0
            last_count = count

        html = page.content()
        browser.close()

    return html


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
try:
    from ..database.sql_utilities import sql_literal
except ImportError:
    from utility.database.sql_utilities import sql_literal


def _store_reviews(link, course_name, reviews):
    """Store reviews in PostgreSQL and return the course's persistent ID."""
    try:
        from ..tools.pg_tools import direct_db_access
    except ImportError:
        from utility.tools.pg_tools import direct_db_access

    direct_db_access(f'CREATE SCHEMA IF NOT EXISTS "{REVIEW_SCHEMA}"')
    direct_db_access("""
        CREATE TABLE IF NOT EXISTS reviews.course_reviews_master (
            unique_id TEXT PRIMARY KEY,
            course_link TEXT NOT NULL UNIQUE,
            course_name TEXT NOT NULL DEFAULT ''
        )
        """)
    _, rows = direct_db_access(
        "SELECT unique_id FROM reviews.course_reviews_master "
        f"WHERE course_link = {sql_literal(link)}"
    )
    if rows:
        unique_id = rows[0][0]
    else:
        candidate_id = uuid.uuid4().hex
        direct_db_access(
            "INSERT INTO reviews.course_reviews_master "
            "(unique_id, course_link, course_name) "
            f"VALUES ({sql_literal(candidate_id)}, {sql_literal(link)}, "
            f"{sql_literal(course_name)}) "
            "ON CONFLICT (course_link) DO NOTHING"
        )
        # Re-read so simultaneous runs use the same persistent course ID.
        _, rows = direct_db_access(
            "SELECT unique_id FROM reviews.course_reviews_master "
            f"WHERE course_link = {sql_literal(link)}"
        )
        unique_id = rows[0][0]

    direct_db_access(
        "UPDATE reviews.course_reviews_master "
        f"SET course_name = {sql_literal(course_name)} "
        f"WHERE unique_id = {sql_literal(unique_id)}"
    )

    # IDs are generated as UUID hex strings and are the only identifier input.
    if not re.fullmatch(r"[0-9a-f]{32}", unique_id):
        raise ValueError("Invalid course ID in course_reviews_master")
    direct_db_access(f"""
        CREATE TABLE IF NOT EXISTS "{REVIEW_SCHEMA}".course_reviews (
            course_id TEXT NOT NULL REFERENCES "{REVIEW_SCHEMA}".course_reviews_master(unique_id),
            review_id TEXT NOT NULL,
            name TEXT NOT NULL,
            review_date DATE,
            date_raw TEXT NOT NULL,
            review TEXT NOT NULL,
            PRIMARY KEY (course_id, review_id)
        )
        """)

    table = f'"{REVIEW_SCHEMA}".course_reviews'
    direct_db_access(f"DELETE FROM {table} WHERE course_id = {sql_literal(unique_id)}")

    # Content-derived keys keep review IDs stable when the table is reloaded.
    for start in range(0, len(reviews), 500):
        values = []
        for item in reviews[start : start + 500]:
            fields = [item["name"], item["date"], item["date_raw"], item["review"]]
            review_id = hashlib.sha256(
                json.dumps(fields, ensure_ascii=False, separators=(",", ":")).encode(
                    "utf-8"
                )
            ).hexdigest()
            values.append(
                "("
                + ", ".join(
                    [
                        sql_literal(review_id),
                        sql_literal(unique_id),
                        sql_literal(item["name"]),
                        sql_literal(item["date"] or None),
                        sql_literal(item["date_raw"]),
                        sql_literal(item["review"]),
                    ]
                )
                + ")"
            )
        if values:
            direct_db_access(
                f"INSERT INTO {table} (review_id, course_id, name, review_date, date_raw, review) "
                f"VALUES {', '.join(values)} ON CONFLICT (course_id, review_id) DO NOTHING"
            )

    return unique_id


def scrape_reviews(link):
    """Scrape reviews and replace the course's stored PostgreSQL data."""
    html = scrape(link)
    reviews = parse_reviews(html)
    _store_reviews(link, course_name_from_html(html, link), reviews)

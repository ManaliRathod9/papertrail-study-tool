# semantic_search.py
# This file talks to the Semantic Scholar API and turns the results into
# the same kind of paper dictionaries we already use for arXiv.

import os
import time
import requests
from dotenv import load_dotenv

# Read the variables from our .env file into the environment, so
# os.getenv() below can find them.
load_dotenv()

# Our Semantic Scholar API key, if we have one set in .env.
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

# Semantic Scholar's public paper search endpoint.
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

# The specific fields we want back for each paper. Asking only for what
# we need keeps the response small and simple to work with.
FIELDS = "title,abstract,authors,year,url,openAccessPdf,citationCount,venue"

# A short pause before each request. Semantic Scholar only allows about
# 1 request per second, so we wait a little longer than that to be safe.
REQUEST_DELAY_SECONDS = 1.1


def clean_text(text):
    """Remove extra spaces and newlines so text looks tidy on screen."""
    if not text:
        return ""
    # Splitting and joining collapses any run of spaces/newlines into one space.
    return " ".join(text.split())


def shorten_summary(text, max_length=500):
    """Cut the summary down so it stays short and easy to read."""
    text = clean_text(text)
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."


def parse_paper(item):
    """Turn one paper from the Semantic Scholar response into our format."""

    title = clean_text(item.get("title"))

    # Authors come back as a list of dictionaries, so we pull out the names.
    author_names = [
        author.get("name", "")
        for author in item.get("authors", []) or []
        if author.get("name")
    ]
    authors = ", ".join(author_names)

    # Year can be missing, so we fall back to an empty string instead of None.
    year = item.get("year") or ""

    # Use the abstract as our summary. Some papers don't have one.
    abstract = item.get("abstract")
    if abstract:
        short_summary = shorten_summary(abstract)
    else:
        short_summary = "No abstract available."

    # Use the link Semantic Scholar gives us for the paper page.
    link = item.get("url") or ""

    # Not every paper has a free PDF available.
    open_access_pdf = item.get("openAccessPdf") or {}
    pdf_link = open_access_pdf.get("url") or ""

    # These two are extra details Semantic Scholar provides that arXiv
    # doesn't, so we fall back to safe defaults if they're missing.
    citation_count = item.get("citationCount") or 0
    venue = item.get("venue") or ""

    return {
        "title": title,
        "authors": authors,
        "year": year,
        "source": "Semantic Scholar",
        "link": link,
        "pdf_link": pdf_link,
        "short_summary": short_summary,
        "citation_count": citation_count,
        "venue": venue,
    }


def search_semantic_scholar(query, max_results=5):
    """
    Search Semantic Scholar for a topic and return a list of paper
    dictionaries. If anything goes wrong (rate limit, no internet, bad
    response, etc.) we print what happened and return an empty list
    instead of letting the app crash.
    """
    params = {
        "query": query,
        "limit": max_results,
        "fields": FIELDS,
    }

    # Always identify our app. Only add the API key header if we
    # actually have one — if it's missing, we still try the request
    # without it (just at the lower, unauthenticated rate limit).
    headers = {"User-Agent": "PaperTrail/1.0"}
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY

    # Pause briefly before calling the API, to be gentle on the rate limit.
    time.sleep(REQUEST_DELAY_SECONDS)

    try:
        response = requests.get(
            SEMANTIC_SCHOLAR_API_URL, params=params, headers=headers, timeout=15
        )

        # Semantic Scholar's free tier is strict about how many requests
        # we can make, so we handle this case on its own with a clear,
        # friendly message instead of a confusing error.
        if response.status_code == 429:
            print("Semantic Scholar rate limit reached. Try again later.")
            return []

        # Any other non-200 response is treated as a normal failure.
        if response.status_code != 200:
            print(f"Semantic Scholar API error: {response.status_code}")
            print(response.text)
            return []

        data = response.json()
        papers = data.get("data", []) or []

        return [parse_paper(paper) for paper in papers]

    except Exception as error:
        # This catches network problems, like no internet connection
        # or a request that timed out.
        print(f"Semantic Scholar request failed: {error}")
        return []

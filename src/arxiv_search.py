# arxiv_search.py
# This file talks to the arXiv API and turns the results into a simple
# list of paper dictionaries that the rest of the app can use.

import requests
import xml.etree.ElementTree as ET

# arXiv's public search API address. We just add a query to the end of it.
ARXIV_API_URL = "http://export.arxiv.org/api/query"

# arXiv replies using the Atom XML format, so we need this namespace
# to read the tags correctly (title, author, summary, and so on).
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


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


def parse_entry(entry):
    """Turn one <entry> from the arXiv feed into a paper dictionary."""

    # Title and summary often come with messy spacing, so we clean them.
    title = clean_text(entry.find("atom:title", ATOM_NS).text)
    summary = shorten_summary(entry.find("atom:summary", ATOM_NS).text)

    # There can be more than one author, so we collect all of their names.
    author_names = [
        clean_text(author.find("atom:name", ATOM_NS).text)
        for author in entry.findall("atom:author", ATOM_NS)
    ]
    authors = ", ".join(author_names)

    # The published date looks like "2017-06-12T17:57:34Z", so the
    # first 4 characters give us the year.
    published = entry.find("atom:published", ATOM_NS).text
    year = published[:4] if published else ""

    # The abstract page link and the PDF link are stored separately.
    abs_link = ""
    pdf_link = ""
    for link in entry.findall("atom:link", ATOM_NS):
        if link.get("title") == "pdf":
            pdf_link = link.get("href")
        elif link.get("rel") == "alternate":
            abs_link = link.get("href")

    return {
        "title": title,
        "authors": authors,
        "year": year,
        "source": "arXiv",
        "link": abs_link,
        "pdf_link": pdf_link,
        "short_summary": summary,
    }


def search_arxiv(query, max_results=5):
    """
    Search arXiv for a topic and return a list of paper dictionaries.
    If anything goes wrong (no internet, bad response, etc.) we return
    an empty list instead of letting the app crash.
    """
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
    }

    try:
        response = requests.get(ARXIV_API_URL, params=params, timeout=10)
        response.raise_for_status()

        # The feed is XML text, so we parse it into a tree we can search.
        root = ET.fromstring(response.text)
        entries = root.findall("atom:entry", ATOM_NS)

        return [parse_entry(entry) for entry in entries]

    except Exception:
        # Anything unexpected (network issue, bad XML, etc.) ends up here.
        return []

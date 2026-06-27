import html

import streamlit as st
import pandas as pd

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

from src.arxiv_search import search_arxiv
from src.semantic_search import search_semantic_scholar
from src.openai_helper import (
    generate_read_summary,
    generate_research_direction,
    generate_project_plan,
    generate_full_guide,
    generate_paper_fit_score,
    generate_skill_gap,
    generate_reading_roadmap,
    generate_github_project_plan,
    generate_project_idea_by_level,
    improve_user_project_idea,
    compare_papers,
)


def shorten_for_card(text, max_chars=220):
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def normalize_title(title):
    return title.lower().strip()


def remove_duplicate_papers(papers):
    """A paper can show up in both arXiv and Semantic Scholar; this keeps the first copy only."""
    seen_titles = set()
    unique_papers = []

    for paper in papers:
        title_key = normalize_title(paper["title"])
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_papers.append(paper)

    return unique_papers


def get_year_value(paper):
    """arXiv gives year as text ("2017"), Semantic Scholar gives a number; missing becomes 0."""
    try:
        return int(paper.get("year") or 0)
    except (TypeError, ValueError):
        return 0


def format_fit_score_as_text(fit_score):
    """Plain-text version of the fit score, used for the TXT/PDF download."""
    lines = [
        f"Reading Fit: {fit_score.get('reading_fit', '?')}/10",
        f"Research Fit: {fit_score.get('research_fit', '?')}/10",
        f"Project Fit: {fit_score.get('project_fit', '?')}/10",
        "",
        f"Difficulty: {fit_score.get('difficulty', '')}",
        f"Best For: {fit_score.get('best_for', '')}",
        "",
        "Reason:",
        fit_score.get("reason", ""),
    ]
    skills = fit_score.get("skills_needed", [])
    if skills:
        lines.append("")
        lines.append("Skills Needed:")
        lines.extend(f"- {skill}" for skill in skills)
    return "\n".join(lines)


def _fit_chip(text):
    return f'<span class="fit-chip">{html.escape(text)}</span>'


def _skill_tag(text):
    return f'<span class="skill-tag">{html.escape(text)}</span>'


def render_fit_score_card(fit_score):
    """Compact on-screen layout for the fit score: chips, a reason box, and skill tags."""
    score_chips = (
        _fit_chip(f"Reading {fit_score.get('reading_fit', '?')}/10")
        + _fit_chip(f"Research {fit_score.get('research_fit', '?')}/10")
        + _fit_chip(f"Project {fit_score.get('project_fit', '?')}/10")
    )
    detail_chips = (
        _fit_chip(f"Difficulty: {fit_score.get('difficulty', '')}")
        + _fit_chip(f"Best For: {fit_score.get('best_for', '')}")
    )

    reason_html = ""
    reason = fit_score.get("reason", "")
    if reason:
        reason_html = (
            '<div class="fit-score-label">Reason</div>'
            f'<div class="fit-score-box">{html.escape(reason)}</div>'
        )

    skills_html = ""
    skills = fit_score.get("skills_needed", [])
    if skills:
        skill_tags = "".join(_skill_tag(skill) for skill in skills)
        skills_html = f'<div class="fit-score-label">Skills Needed</div><div>{skill_tags}</div>'

    st.markdown(
        f'<div class="fit-score">'
        f"<div>{score_chips}</div>"
        f"<div>{detail_chips}</div>"
        f"{reason_html}"
        f"{skills_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


# Shared between the table view and the downloadable text version, so
# they can never drift out of sync with each other.
COMPARISON_AREA_ROWS = [
    ("Main topic", "main_topic"),
    ("Method or approach", "method_or_approach"),
    ("Strength", "strength"),
    ("Limitation", "limitation"),
    ("Difficulty", "difficulty"),
    ("Project potential", "project_potential"),
    ("Best use", "best_use"),
]
COMPARISON_RECOMMENDATION_ROWS = [
    ("Better for reading", "better_for_reading"),
    ("Better for research", "better_for_research"),
    ("Better for project", "better_for_project"),
    ("Better for resume", "better_for_resume"),
    ("Final recommendation", "final_recommendation"),
]


def render_comparison_tables(comparison):
    paper_comparison = comparison.get("paper_comparison", {})
    recommendation = comparison.get("recommendation", {})

    table1 = pd.DataFrame([
        {
            "Area": label,
            "Paper 1": paper_comparison.get(key, {}).get("paper1", ""),
            "Paper 2": paper_comparison.get(key, {}).get("paper2", ""),
        }
        for label, key in COMPARISON_AREA_ROWS
    ])

    table2 = pd.DataFrame([
        {"Question": label, "Recommendation": recommendation.get(key, "")}
        for label, key in COMPARISON_RECOMMENDATION_ROWS
    ])

    st.write("**Paper comparison**")
    st.table(table1)

    st.write("**Recommendation**")
    st.table(table2)


def format_comparison_as_text(comparison):
    """Same data as render_comparison_tables, as plain text for the TXT/PDF download."""
    paper_comparison = comparison.get("paper_comparison", {})
    recommendation = comparison.get("recommendation", {})

    lines = ["Paper comparison", ""]
    for label, key in COMPARISON_AREA_ROWS:
        area = paper_comparison.get(key, {})
        lines.append(f"{label}:")
        lines.append(f"  Paper 1: {area.get('paper1', '')}")
        lines.append(f"  Paper 2: {area.get('paper2', '')}")
        lines.append("")

    lines.append("Recommendation")
    lines.append("")
    for label, key in COMPARISON_RECOMMENDATION_ROWS:
        lines.append(f"{label}: {recommendation.get(key, '')}")

    return "\n".join(lines)


def safe_filename(text):
    cleaned = "".join(ch if (ch.isalnum() or ch in " _-") else " " for ch in text)
    cleaned = "_".join(cleaned.split())
    return cleaned.lower().strip("_") or "result"


def create_pdf_bytes(title, content):
    """Returns PDF bytes using fpdf2's built-in font, or None if that isn't possible."""
    if not FPDF_AVAILABLE:
        return None

    try:
        # Core fonts only support Latin-1, so anything outside that
        # range (smart quotes, em dashes, etc.) gets replaced instead
        # of raising an encoding error.
        def to_latin1(text):
            return text.encode("latin-1", errors="replace").decode("latin-1")

        pdf = FPDF()
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(0, 8, to_latin1(title))
        pdf.ln(4)

        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, to_latin1(content))

        return bytes(pdf.output())
    except Exception:
        return None


def display_ai_output(title, content, key_prefix, paper_title="", render_func=None):
    """
    Shared card for every AI result: expander and TXT/PDF download buttons.
    `content` is always the plain-text version used for the downloads.
    If `render_func` is given, it's called to draw the on-screen view
    instead of st.markdown(content) - used for Fit Score's layout.
    """
    with st.container(border=True):
        st.markdown(f"**{title}**")

        with st.expander("View result", expanded=True):
            if render_func:
                render_func()
            else:
                st.markdown(content)

            file_text = f"{title}\n"
            if paper_title:
                file_text += f"Paper: {paper_title}\n"
            file_text += f"\n{content}"

            file_base = safe_filename(title)

            download_col1, download_col2 = st.columns(2)
            with download_col1:
                st.download_button(
                    "Download as TXT",
                    data=file_text,
                    file_name=f"{file_base}.txt",
                    mime="text/plain",
                    key=f"{key_prefix}_txt_download",
                )
            with download_col2:
                pdf_bytes = create_pdf_bytes(title, file_text)
                if pdf_bytes is not None:
                    st.download_button(
                        "Download as PDF",
                        data=pdf_bytes,
                        file_name=f"{file_base}.pdf",
                        mime="application/pdf",
                        key=f"{key_prefix}_pdf_download",
                    )
                else:
                    st.caption("PDF download isn't available right now.")


def build_saved_papers_dataframe():
    rows = []
    for saved_paper in st.session_state["saved_papers"]:
        note_key = normalize_title(saved_paper["title"])
        rows.append({
            "title": saved_paper.get("title", ""),
            "authors": saved_paper.get("authors", ""),
            "year": saved_paper.get("year", ""),
            "source": saved_paper.get("source", ""),
            "link": saved_paper.get("link", ""),
            "pdf_link": saved_paper.get("pdf_link", ""),
            "notes": st.session_state["saved_notes"].get(note_key, ""),
        })
    return pd.DataFrame(rows)


def build_saved_papers_markdown():
    lines = ["# Saved Papers", ""]
    for saved_paper in st.session_state["saved_papers"]:
        note_key = normalize_title(saved_paper["title"])
        note = st.session_state["saved_notes"].get(note_key, "")
        lines.append(f"## {saved_paper.get('title', '')}")
        lines.append("")
        lines.append(f"Authors: {saved_paper.get('authors', '')}")
        lines.append(f"Year: {saved_paper.get('year', '')}")
        lines.append(f"Source: {saved_paper.get('source', '')}")
        lines.append(f"Link: {saved_paper.get('link', '')}")
        lines.append(f"Notes: {note}")
        lines.append("")
    return "\n".join(lines)


GOAL_GUIDANCE = {
    "Read": "Use this mode when you want to understand the paper before "
            "doing anything else. Start with the abstract, introduction, "
            "and conclusion.",
    "Research": "Use this mode when you want to explore research gaps, "
                "future work, or thesis/PhD direction. Focus on "
                "limitations, related work, and open questions.",
    "Build": "Use this mode when you want to turn a paper into a "
              "practical project. Look for the method, dataset, "
              "baseline, and evaluation metric.",
    "Full Guide": "Use this mode when you want the full path: "
                  "understand the paper, find research direction, and "
                  "convert it into a project plan.",
}

GOAL_GENERATORS = {
    "Read": generate_read_summary,
    "Research": generate_research_direction,
    "Build": generate_project_plan,
    "Full Guide": generate_full_guide,
}

GOAL_BUTTON_LABELS = {
    "Read": "Explain this paper",
    "Research": "Find research direction",
    "Build": "Turn into project",
    "Full Guide": "Create full guide",
}

GOAL_SPINNER_TEXT = {
    "Read": "Explaining the paper...",
    "Research": "Finding research direction...",
    "Build": "Creating project plan...",
    "Full Guide": "Creating full guide...",
}

# Used as the result card's title and the base of its downloaded filename.
GOAL_OUTPUT_LABELS = {
    "Read": "Paper Explanation",
    "Research": "Research Direction",
    "Build": "Project Plan",
    "Full Guide": "Full Guide",
}

SEARCH_TYPE_LABELS = {
    "Topic": "What topic are you exploring?",
    "Paper Title": "Enter a paper title or part of a title",
    "Author Name": "Enter an author name",
}

# "Recent papers" and "Highly cited papers" don't add to the query;
# they sort the results after fetching instead (see search_clicked below).
SEARCH_GOAL_QUERY_SUFFIXES = {
    "Any": "",
    "Beginner friendly": " introduction survey overview",
    "Good for project": " dataset method evaluation implementation",
    "Good for research": " research gap future work survey",
    "Recent papers": "",
    "Highly cited papers": "",
}

# Result keys look like "Read_0" or "fit_score_2"; these prefixes let
# clear_all_ai_results() find and remove all of them at once.
RESULT_KEY_PREFIXES = list(GOAL_GENERATORS.keys()) + [
    "fit_score", "skill_gap", "reading_plan", "github_plan",
    "project_idea", "editable_idea", "improved_idea",
]


def clear_all_ai_results():
    for key in list(st.session_state.keys()):
        if any(key.startswith(f"{prefix}_") for prefix in RESULT_KEY_PREFIXES):
            del st.session_state[key]


def build_search_query(base_query, search_goal):
    suffix = SEARCH_GOAL_QUERY_SUFFIXES.get(search_goal, "")
    return f"{base_query}{suffix}".strip()


st.set_page_config(page_title="PaperTrail", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0F1117;
        color: #F5F7FA;
    }

    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                     Roboto, Helvetica, Arial, sans-serif;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #F5F7FA;
    }

    /* Streamlit's own theme sets paragraph/list text color with higher
       specificity than .stApp above, which is what made AI output text
       render too dark on this dark background. This forces it bright. */
    .stMarkdown p, .stMarkdown li, .stMarkdown span, .stMarkdown strong {
        color: #F5F7FA !important;
    }

    [data-testid="stCaptionContainer"] {
        color: #A8ADB7 !important;
    }

    .muted-label {
        color: #A8ADB7;
        font-size: 0.85rem;
    }

    /* Search panel, paper cards, saved paper cards, AI output cards,
       and the comparison section all use bordered containers, so
       styling this one selector turns all of them into consistent
       cards (this is the "ai-output-card" look). */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #171B24;
        border: 1px solid #343B4A;
        border-radius: 14px;
        padding: 0.4rem 0.2rem;
    }

    [data-testid="stExpander"] {
        background-color: #1D2330;
        border: 1px solid #343B4A;
        border-radius: 10px;
    }

    .stButton > button, .stDownloadButton > button {
        border-radius: 8px;
        border: 1px solid #343B4A;
        padding: 0.45rem 1rem;
    }

    /* Primary buttons (Search Papers) get the accent color. */
    .stButton > button[kind="primary"] {
        background-color: #8EA7FF;
        color: #0F1117;
        border: none;
    }
    .stButton > button[kind="primary"]:hover {
        filter: brightness(1.1);
    }

    .stButton > button[kind="secondary"] {
        background-color: #1D2330;
        color: #F5F7FA;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #8EA7FF;
        color: #8EA7FF;
    }

    .stTextInput input, .stTextArea textarea {
        background-color: #1D2330;
        color: #F5F7FA;
        border-radius: 8px;
        border: 1px solid #343B4A;
    }

    div[data-baseweb="select"] > div {
        background-color: #1D2330;
        border-radius: 8px;
        border: 1px solid #343B4A;
    }

    div[data-testid="stAlert"] {
        border-radius: 10px;
    }

    /* Fit Score chips, skill tags, and labels (see render_fit_score_card). */
    .fit-score > div {
        margin-bottom: 0.4rem;
    }

    .fit-chip {
        display: inline-block;
        background-color: #1D2330;
        color: #F5F7FA;
        border: 1px solid #343B4A;
        border-radius: 8px;
        padding: 0.35rem 0.8rem;
        margin: 0 0.4rem 0.4rem 0;
        font-size: 0.9rem;
        font-weight: 500;
    }

    .skill-tag {
        display: inline-block;
        background-color: #1D2330;
        color: #F5F7FA;
        border: 1px solid #343B4A;
        border-radius: 999px;
        padding: 0.3rem 0.8rem;
        margin: 0 0.4rem 0.4rem 0;
        font-size: 0.85rem;
    }

    .fit-score-label {
        color: #DDE3EA;
        font-weight: 600;
        font-size: 0.9rem;
    }

    .fit-score-box {
        background-color: #1D2330;
        border: 1px solid #343B4A;
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        color: #F5F7FA;
        font-size: 0.95rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "saved_papers" not in st.session_state:
    st.session_state["saved_papers"] = []
if "saved_notes" not in st.session_state:
    st.session_state["saved_notes"] = {}
if "selected_papers" not in st.session_state:
    st.session_state["selected_papers"] = []

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "search"

# Streamlit blocks writing to a widget's session_state key after that
# widget has already been created in the same run. Clear Search can't
# reset "search_query" directly (the text box below it already exists
# by the time the button is clicked), so it sets this flag and reruns;
# this check, running before the text box is created, does the reset.
if st.session_state.get("clear_search_now", False):
    st.session_state["search_query"] = ""
    st.session_state["clear_search_now"] = False


if st.session_state["current_page"] == "search":

    header_left, header_center, header_right = st.columns([1, 3, 2])

    with header_center:
        st.markdown(
            """
            <div style="text-align: center; padding-top: 0.5rem;">
                <h1 style="margin-bottom: 0.2rem;">PaperTrail</h1>
                <p style="color: #A8ADB7; margin: 0 0 0.6rem 0;">
                    Find papers. Understand them. Decide what to do next.
                </p>
                <span style="
                    display: inline-block;
                    background-color: #1B1F2A;
                    color: #A8ADB7;
                    border: 1px solid #2A2F3A;
                    border-radius: 999px;
                    padding: 0.25rem 0.9rem;
                    font-size: 0.8rem;
                ">
                    Research paper discovery • Reading help • Project planning
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with header_right:
        nav_col1, nav_col2 = st.columns(2)
        with nav_col1:
            saved_count = len(st.session_state["saved_papers"])
            if st.button(f"Saved Papers ({saved_count})"):
                st.session_state["current_page"] = "saved"
                st.rerun()
        with nav_col2:
            if st.button("Compare Papers"):
                st.session_state["current_page"] = "compare"
                st.rerun()

    st.write("")

    with st.container(border=True):
        st.markdown("### Start your search")

        search_type = st.selectbox(
            "What do you want to search by?",
            ["Topic", "Paper Title", "Author Name"]
        )

        topic = st.text_input(SEARCH_TYPE_LABELS[search_type], key="search_query")

        goal = st.selectbox(
            "What do you want to do?",
            ["Read", "Research", "Build", "Full Guide"]
        )

        st.write("Where do you want to search?")
        use_arxiv = st.checkbox("arXiv", value=True)
        use_semantic_scholar = st.checkbox("Semantic Scholar", value=True)

        result_count = st.selectbox(
            "How many papers per source do you want to see?",
            [5, 10, 15, 20]
        )

        search_goal = st.selectbox(
            "What kind of papers do you want?",
            ["Any", "Beginner friendly", "Good for project", "Good for research",
             "Recent papers", "Highly cited papers"]
        )

        search_col, clear_col = st.columns(2)
        with search_col:
            search_clicked = st.button("Search Papers", type="primary")
        with clear_col:
            clear_clicked = st.button("Clear Search")

    # Results are saved into session_state, not local variables, since
    # Streamlit reruns this whole script on every button click
    # (including ones further down, like "Save paper" or "Check fit").
    # Without that, search_clicked would be False on those reruns and
    # the results section would disappear.
    if search_clicked:
        if not topic.strip():
            st.warning("Please type something to search for.")
        elif not use_arxiv and not use_semantic_scholar:
            st.warning("Please select at least one source.")
        else:
            search_query_text = build_search_query(topic, search_goal)

            arxiv_papers = []
            if use_arxiv:
                arxiv_papers = search_arxiv(search_query_text, max_results=result_count)

            semantic_papers = []
            if use_semantic_scholar:
                semantic_papers = search_semantic_scholar(search_query_text, max_results=result_count)

            papers = remove_duplicate_papers(arxiv_papers + semantic_papers)

            if search_goal == "Recent papers":
                papers = sorted(papers, key=get_year_value, reverse=True)
            elif search_goal == "Highly cited papers":
                papers = sorted(papers, key=lambda p: p.get("citation_count") or 0, reverse=True)

            st.session_state["topic"] = topic
            st.session_state["goal"] = goal
            st.session_state["result_count"] = result_count
            st.session_state["arxiv_count"] = len(arxiv_papers)
            st.session_state["semantic_count"] = len(semantic_papers)
            st.session_state["search_results"] = papers

            st.session_state["selected_papers"] = []
            if "comparison_result" in st.session_state:
                del st.session_state["comparison_result"]

            clear_all_ai_results()

    if clear_clicked:
        st.session_state["clear_search_now"] = True

        for key in ("topic", "goal", "result_count", "arxiv_count", "semantic_count",
                    "search_results", "comparison_result"):
            if key in st.session_state:
                del st.session_state[key]

        st.session_state["selected_papers"] = []
        clear_all_ai_results()

        st.session_state["just_cleared"] = True
        st.rerun()

    if st.session_state.pop("just_cleared", False):
        st.info("Search cleared. Saved papers are still available.")

    if st.session_state.pop("just_saved", False):
        st.success("Paper saved.")

    if "search_results" in st.session_state:
        st.write("")
        st.subheader("Results")

        with st.container(border=True):
            st.caption(f"Query: {st.session_state['topic']}")
            st.caption(f"Goal: {st.session_state['goal']}")
            st.caption(
                f"Showing up to {st.session_state['result_count']} papers per "
                "selected source, ranked by search relevance."
            )
            st.caption(
                f"arXiv results: {st.session_state['arxiv_count']} · "
                f"Semantic Scholar results: {st.session_state['semantic_count']}"
            )

        st.info(GOAL_GUIDANCE[st.session_state["goal"]])

        st.write("")

        papers = st.session_state["search_results"]

        if not papers:
            st.info("No papers found. Try a broader topic.")
        else:
            selected_papers = []

            for index, paper in enumerate(papers):
                with st.container(border=True):
                    title_col, save_col = st.columns([4, 1])
                    with title_col:
                        st.markdown(f"##### {paper['title']}")
                    with save_col:
                        saved_titles = [
                            normalize_title(saved["title"])
                            for saved in st.session_state["saved_papers"]
                        ]
                        if normalize_title(paper["title"]) in saved_titles:
                            st.write("♥ Saved")
                        elif st.button("♡ Save", key=f"save_{index}"):
                            st.session_state["saved_papers"].append(paper)
                            st.session_state["just_saved"] = True
                            st.rerun()

                    st.caption(f"{paper['authors']} · {paper['year']} · {paper['source']}")
                    st.write(shorten_for_card(paper["short_summary"]))

                    col1, col2 = st.columns(2)
                    with col1:
                        if paper["link"]:
                            st.link_button("Read paper", paper["link"], key=f"read_{index}")
                    with col2:
                        if paper["pdf_link"]:
                            st.link_button("PDF", paper["pdf_link"], key=f"pdf_{index}")
                        else:
                            st.caption("PDF not available")

                    # Includes the goal in the key (e.g. "Read_0") so
                    # switching goals never shows a stale result from
                    # a different goal for the same paper.
                    result_key = f"{goal}_{index}"

                    button_label = GOAL_BUTTON_LABELS[goal]
                    spinner_text = GOAL_SPINNER_TEXT[goal]
                    generate_result = GOAL_GENERATORS[goal]

                    if st.button(button_label, key=f"action_{index}"):
                        with st.spinner(spinner_text):
                            result = generate_result(paper["title"], paper["short_summary"])
                        st.session_state[result_key] = result

                    if result_key in st.session_state:
                        display_ai_output(
                            GOAL_OUTPUT_LABELS[goal],
                            st.session_state[result_key],
                            key_prefix=result_key,
                            paper_title=paper["title"],
                        )

                    if st.checkbox("Select for comparison", key=f"compare_{index}"):
                        selected_papers.append(paper)

                    with st.expander("AI tools for this paper"):
                        fit_key = f"fit_score_{index}"
                        if st.button("Check fit", key=f"fit_button_{index}"):
                            with st.spinner("Checking fit..."):
                                st.session_state[fit_key] = generate_paper_fit_score(
                                    paper["title"], paper["short_summary"]
                                )
                        if fit_key in st.session_state:
                            fit_result = st.session_state[fit_key]
                            if isinstance(fit_result, dict):
                                display_ai_output(
                                    "Fit Score",
                                    format_fit_score_as_text(fit_result),
                                    key_prefix=fit_key,
                                    paper_title=paper["title"],
                                    render_func=lambda fit_result=fit_result: render_fit_score_card(fit_result),
                                )
                            else:
                                display_ai_output(
                                    "Fit Score", fit_result, key_prefix=fit_key, paper_title=paper["title"]
                                )

                        st.write("")

                        skill_key = f"skill_gap_{index}"
                        if st.button("Skill gap", key=f"skill_button_{index}"):
                            with st.spinner("Finding what to learn first..."):
                                st.session_state[skill_key] = generate_skill_gap(
                                    paper["title"], paper["short_summary"]
                                )
                        if skill_key in st.session_state:
                            display_ai_output(
                                "Skill Gap", st.session_state[skill_key],
                                key_prefix=skill_key, paper_title=paper["title"],
                            )

                        st.write("")

                        plan_key = f"reading_plan_{index}"
                        if st.button("Reading plan", key=f"plan_button_{index}"):
                            with st.spinner("Building a reading plan..."):
                                st.session_state[plan_key] = generate_reading_roadmap(
                                    paper["title"], paper["short_summary"]
                                )
                        if plan_key in st.session_state:
                            display_ai_output(
                                "Reading Plan", st.session_state[plan_key],
                                key_prefix=plan_key, paper_title=paper["title"],
                            )

                        if goal in ("Build", "Full Guide"):
                            st.write("")
                            st.markdown("**Project ideas from this paper**")

                            idea_col1, idea_col2, idea_col3 = st.columns(3)
                            with idea_col1:
                                beginner_idea_clicked = st.button(
                                    "Beginner idea", key=f"idea_beginner_{index}"
                                )
                            with idea_col2:
                                intermediate_idea_clicked = st.button(
                                    "Intermediate idea", key=f"idea_intermediate_{index}"
                                )
                            with idea_col3:
                                advanced_idea_clicked = st.button(
                                    "Advanced idea", key=f"idea_advanced_{index}"
                                )

                            if beginner_idea_clicked:
                                with st.spinner("Creating a Beginner project idea..."):
                                    st.session_state[f"project_idea_{index}_Beginner"] = (
                                        generate_project_idea_by_level(
                                            paper["title"], paper["short_summary"], "Beginner"
                                        )
                                    )
                            if intermediate_idea_clicked:
                                with st.spinner("Creating an Intermediate project idea..."):
                                    st.session_state[f"project_idea_{index}_Intermediate"] = (
                                        generate_project_idea_by_level(
                                            paper["title"], paper["short_summary"], "Intermediate"
                                        )
                                    )
                            if advanced_idea_clicked:
                                with st.spinner("Creating an Advanced project idea..."):
                                    st.session_state[f"project_idea_{index}_Advanced"] = (
                                        generate_project_idea_by_level(
                                            paper["title"], paper["short_summary"], "Advanced"
                                        )
                                    )

                            # Editing is always optional: the generated
                            # idea can be used as-is, or replaced/edited
                            # below before improving it.
                            for level in ("Beginner", "Intermediate", "Advanced"):
                                idea_key = f"project_idea_{index}_{level}"
                                if idea_key not in st.session_state:
                                    continue

                                display_ai_output(
                                    f"Project Idea ({level})", st.session_state[idea_key],
                                    key_prefix=idea_key, paper_title=paper["title"],
                                )
                                st.caption("Use this idea as-is, or edit it below.")

                                editable_key = f"editable_idea_{index}_{level}"
                                # Pre-filled with the generated idea on
                                # first render; after that, the widget
                                # keeps whatever the user typed.
                                edited_text = st.text_area(
                                    "Edit this idea or write your own idea",
                                    value=st.session_state.get(editable_key, st.session_state[idea_key]),
                                    key=f"editable_idea_input_{index}_{level}",
                                )
                                st.session_state[editable_key] = edited_text

                                if st.button("Improve my edited idea", key=f"improve_idea_{index}_{level}"):
                                    if not edited_text.strip():
                                        st.warning("Please write or generate an idea first.")
                                    else:
                                        with st.spinner("Improving the idea..."):
                                            st.session_state[f"improved_idea_{index}_{level}"] = (
                                                improve_user_project_idea(
                                                    paper["title"], paper["short_summary"], edited_text
                                                )
                                            )

                                improved_key = f"improved_idea_{index}_{level}"
                                if improved_key in st.session_state:
                                    display_ai_output(
                                        f"Improved Idea ({level})", st.session_state[improved_key],
                                        key_prefix=improved_key, paper_title=paper["title"],
                                    )

                                st.write("")

                            st.write("")
                            st.markdown("**GitHub plan**")

                            github_col1, github_col2, github_col3 = st.columns(3)
                            with github_col1:
                                beginner_github_clicked = st.button(
                                    "Beginner GitHub Plan", key=f"github_beginner_{index}"
                                )
                            with github_col2:
                                intermediate_github_clicked = st.button(
                                    "Intermediate GitHub Plan", key=f"github_intermediate_{index}"
                                )
                            with github_col3:
                                advanced_github_clicked = st.button(
                                    "Advanced GitHub Plan", key=f"github_advanced_{index}"
                                )

                            if beginner_github_clicked:
                                with st.spinner("Creating a Beginner GitHub plan..."):
                                    st.session_state[f"github_plan_{index}_Beginner"] = (
                                        generate_github_project_plan(
                                            paper["title"], paper["short_summary"], "Beginner"
                                        )
                                    )
                            if intermediate_github_clicked:
                                with st.spinner("Creating an Intermediate GitHub plan..."):
                                    st.session_state[f"github_plan_{index}_Intermediate"] = (
                                        generate_github_project_plan(
                                            paper["title"], paper["short_summary"], "Intermediate"
                                        )
                                    )
                            if advanced_github_clicked:
                                with st.spinner("Creating an Advanced GitHub plan..."):
                                    st.session_state[f"github_plan_{index}_Advanced"] = (
                                        generate_github_project_plan(
                                            paper["title"], paper["short_summary"], "Advanced"
                                        )
                                    )

                            for level in ("Beginner", "Intermediate", "Advanced"):
                                level_key = f"github_plan_{index}_{level}"
                                if level_key in st.session_state:
                                    display_ai_output(
                                        f"GitHub Plan ({level})", st.session_state[level_key],
                                        key_prefix=level_key, paper_title=paper["title"],
                                    )

                st.write("")

            if len(selected_papers) > 2:
                st.warning("You can compare only two papers at a time.")

            st.session_state["selected_papers"] = selected_papers

            if len(selected_papers) != 2 and "comparison_result" in st.session_state:
                del st.session_state["comparison_result"]


elif st.session_state["current_page"] == "saved":

    if st.button("Back to Search"):
        st.session_state["current_page"] = "search"
        st.rerun()

    st.markdown(
        """
        <div style="text-align: center; margin: 0.5rem 0 1.5rem 0;">
            <h1 style="margin-bottom: 0;">Saved Papers</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state["saved_papers"]:
        st.write("No saved papers yet.")
    else:
        for saved_index, saved_paper in enumerate(st.session_state["saved_papers"]):
            # Keyed by title, not list position, so a note stays
            # attached to the right paper even after removing another one.
            note_key = normalize_title(saved_paper["title"])

            with st.container(border=True):
                st.markdown(f"##### {saved_paper['title']}")
                st.caption(
                    f"{saved_paper.get('authors', '')} · "
                    f"{saved_paper.get('year', '')} · "
                    f"{saved_paper.get('source', '')}"
                )

                link_col, pdf_col = st.columns(2)
                with link_col:
                    if saved_paper.get("link"):
                        st.link_button("Read paper", saved_paper["link"], key=f"saved_read_{saved_index}")
                with pdf_col:
                    if saved_paper.get("pdf_link"):
                        st.link_button("PDF", saved_paper["pdf_link"], key=f"saved_pdf_{saved_index}")

                note_text = st.text_area(
                    "Notes",
                    value=st.session_state["saved_notes"].get(note_key, ""),
                    key=f"note_input_{note_key}",
                )
                st.session_state["saved_notes"][note_key] = note_text

                if st.button("Remove", key=f"remove_saved_{saved_index}"):
                    st.session_state["saved_papers"].pop(saved_index)
                    st.session_state["saved_notes"].pop(note_key, None)
                    st.rerun()

            st.write("")

        export_col1, export_col2 = st.columns(2)
        with export_col1:
            st.download_button(
                "Download saved papers as CSV",
                data=build_saved_papers_dataframe().to_csv(index=False),
                file_name="saved_papers.csv",
                mime="text/csv",
            )
        with export_col2:
            st.download_button(
                "Download saved papers as Markdown",
                data=build_saved_papers_markdown(),
                file_name="saved_papers.md",
                mime="text/markdown",
            )

        if st.button("Clear all saved papers"):
            st.session_state["saved_papers"] = []
            st.session_state["saved_notes"] = {}
            st.rerun()


elif st.session_state["current_page"] == "compare":

    if st.button("Back to Search"):
        st.session_state["current_page"] = "search"
        st.rerun()

    st.markdown(
        """
        <div style="text-align: center; margin: 0.5rem 0 1.5rem 0;">
            <h1 style="margin-bottom: 0;">Compare Papers</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_papers = st.session_state["selected_papers"]

    if len(selected_papers) > 2:
        st.warning(
            "You have more than two papers selected. Go back to Search "
            "and uncheck one before comparing."
        )
    elif len(selected_papers) < 2:
        st.write("Select two papers from the search results to compare.")
    else:
        st.write(f"Paper 1: {selected_papers[0]['title']}")
        st.write(f"Paper 2: {selected_papers[1]['title']}")

        if st.button("Compare selected papers"):
            with st.spinner("Comparing papers..."):
                comparison_result = compare_papers(selected_papers[0], selected_papers[1])
            st.session_state["comparison_result"] = comparison_result

        if "comparison_result" in st.session_state:
            comparison_result = st.session_state["comparison_result"]
            both_titles = f"{selected_papers[0]['title']} vs {selected_papers[1]['title']}"

            if isinstance(comparison_result, dict):
                with st.container(border=True):
                    render_comparison_tables(comparison_result)

                # A table can't be exported to TXT/PDF directly, so the
                # same data is also offered as a downloadable summary.
                display_ai_output(
                    "Comparison Summary",
                    format_comparison_as_text(comparison_result),
                    key_prefix="comparison_result",
                    paper_title=both_titles,
                )
            else:
                display_ai_output(
                    "Comparison Result", comparison_result,
                    key_prefix="comparison_result", paper_title=both_titles,
                )

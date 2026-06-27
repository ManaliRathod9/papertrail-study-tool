import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SYSTEM_INSTRUCTIONS = (
    "You explain research papers in simple, friendly language for "
    "beginners. Avoid jargon."
)


def test_openai_connection():
    """Returns a status string instead of raising, so it's safe to call directly."""
    if not OPENAI_API_KEY:
        return "OpenAI API key is missing."

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say hello in one word."}],
            max_tokens=5,
        )
        return "OpenAI connection successful."

    except Exception as error:
        return str(error)


def _call_openai(prompt, max_tokens):
    """Shared by every plain-text generator function below."""
    if not OPENAI_API_KEY:
        return "OpenAI API key is missing."

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    except Exception as error:
        return str(error)


def _call_openai_json(prompt, max_tokens):
    """Like _call_openai, but parses the reply as JSON, falling back to raw text if parsing fails."""
    if not OPENAI_API_KEY:
        return "OpenAI API key is missing."

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        reply_text = response.choices[0].message.content.strip()

    except Exception as error:
        return str(error)

    try:
        return json.loads(reply_text)
    except json.JSONDecodeError:
        return reply_text


def _ask_openai_about_paper(title, abstract, instructions, max_tokens=400):
    """Builds the title/abstract prompt shared by every per-paper generator below."""
    if not title or not abstract:
        return "We need both a title and an abstract to do this."

    prompt = f"Paper title: {title}\nAbstract: {abstract}\n\n{instructions}"
    return _call_openai(prompt, max_tokens)


def generate_read_summary(title, abstract):
    instructions = (
        "Explain this paper for a beginner. Keep it short and simple, "
        "and use exactly these five labeled sections:\n"
        "Simple Summary: a plain-language overview in 1-2 sentences\n"
        "Main Problem: the problem this paper is trying to solve\n"
        "Main Idea: the core idea or method, in simple words\n"
        "Why It Matters: why this is useful or worth caring about\n"
        "Difficulty Level: Beginner, Intermediate, or Advanced, with a short reason"
    )
    return _ask_openai_about_paper(title, abstract, instructions, max_tokens=350)


def generate_research_direction(title, abstract):
    instructions = (
        "Help a beginner researcher think about what to explore next "
        "based on this paper. Keep it short, simple, and useful for "
        "someone considering research or a PhD. Use exactly these "
        "seven labeled sections:\n"
        "Research Gap: what this paper does not fully solve or explain\n"
        "What Is Missing In This Paper: a specific weak spot or missing piece\n"
        "What Can Be Improved: a realistic way to improve on this paper\n"
        "Future Work: what the next logical step could be\n"
        "Possible Research Questions: 2-3 simple questions worth asking\n"
        "Thesis or PhD Direction: a possible direction to study further\n"
        "What to Read Next: the kind of papers or topics to look at next"
    )
    return _ask_openai_about_paper(title, abstract, instructions, max_tokens=500)


def generate_project_plan(title, abstract):
    instructions = (
        "Help someone turn this paper into a practical project. Keep it "
        "short, simple, and human, with no buzzwords. Reply using "
        "exactly these ten section headings, in this exact order, each "
        "followed by a colon and then your answer. Do not skip any "
        "section, even if your answer for it is short:\n\n"
        "Beginner Project Option: a small, realistic project a student "
        "could finish, using simple tools\n"
        "Intermediate Project Option: a more complete app or ML/data "
        "pipeline, with more features or a more realistic setup\n"
        "Advanced Project Option: a project that feels research or "
        "industry level, closer to what the original paper did\n"
        "Dataset Suggestion: a dataset that could be used\n"
        "Tech Stack: simple tools or libraries to build it with\n"
        "Step-by-Step Build Plan: 3-5 short steps to get started\n"
        "Evaluation Metrics: how to check if the project works well\n"
        "GitHub Project Title: a short, clear repository name\n"
        "README Outline: a short list of sections a README should have\n"
        "Resume Bullet: one short sentence to describe this project on a resume"
    )
    return _ask_openai_about_paper(title, abstract, instructions, max_tokens=800)


def generate_full_guide(title, abstract):
    instructions = (
        "Give someone the full picture for this paper: understanding it, "
        "a research direction, and a project idea. Keep it short, "
        "simple, and human, with no buzzwords. Reply using exactly "
        "these twelve section headings, in this exact order, each "
        "followed by a colon and then your answer. Do not skip any "
        "section, even if your answer for it is short:\n\n"
        "Simple Summary: a plain-language overview in 1-2 sentences\n"
        "Research Gap: what this paper does not fully solve or explain\n"
        "Beginner Project Option: a small, realistic project a student "
        "could finish, using simple tools\n"
        "Intermediate Project Option: a more complete app or ML/data "
        "pipeline, with more features or a more realistic setup\n"
        "Advanced Project Option: a project that feels research or "
        "industry level, closer to what the original paper did\n"
        "Dataset Suggestion: a dataset that could be used\n"
        "Tech Stack: simple tools or libraries to build it with\n"
        "Build Roadmap: 3-5 short steps to get started\n"
        "Evaluation Metrics: how to check if the project works well\n"
        "GitHub Project Title: a short, clear repository name\n"
        "README Outline: a short list of sections a README should have\n"
        "Resume Bullet: one short sentence to describe this project on a resume"
    )
    return _ask_openai_about_paper(title, abstract, instructions, max_tokens=950)


def generate_skill_gap(title, abstract):
    instructions = (
        "Help a beginner get ready to read this paper. Keep it short, "
        "simple, and practical. Use exactly these four labeled "
        "sections:\n"
        "What You Should Know Before Reading: the background knowledge needed\n"
        "Terms to Learn First: 3-5 key terms used in this paper\n"
        "Beginner-Friendly Explanation: explain those terms in plain words\n"
        "Suggested Learning Order: the order to learn these things in"
    )
    return _ask_openai_about_paper(title, abstract, instructions, max_tokens=450)


def generate_reading_roadmap(title, abstract):
    instructions = (
        "Help a beginner read this paper efficiently in one sitting. "
        "Keep it short, simple, and practical. Use exactly these six "
        "labeled sections:\n"
        "First 10 Minutes: what to read and look for first\n"
        "Next 20 Minutes: what to read and look for next\n"
        "Section to Focus On: the most important part of the paper\n"
        "What Can Be Skipped on First Read: parts that can wait\n"
        "3 Questions to Ask While Reading: simple questions to keep in mind\n"
        "Notes Template: a short template for taking notes on this paper"
    )
    return _ask_openai_about_paper(title, abstract, instructions, max_tokens=500)


# Distinct guidance per level, so a "Beginner" GitHub plan actually
# reads simpler than an "Advanced" one instead of sounding the same.
GITHUB_PLAN_LEVEL_GUIDANCE = {
    "Beginner": (
        "Make this a simple, realistic project a student could finish: "
        "a small frontend/demo, or a small data analysis. Use a simple "
        "folder structure, an easy README, a beginner-friendly dataset "
        "suggestion, and basic evaluation."
    ),
    "Intermediate": (
        "Make this a more complete project: a data pipeline or a real "
        "ML/NLP implementation. Use a proper folder structure, include "
        "preprocessing and evaluation steps, and mention a Streamlit or "
        "FastAPI option for showing it off."
    ),
    "Advanced": (
        "Make this feel research or industry level: reproduce or "
        "extend the paper's idea, compare against a baseline, mention "
        "experiment tracking, include a deployment option, use "
        "stronger evaluation, and list future improvements."
    ),
}


def generate_github_project_plan(title, abstract, level):
    """Generates only the given level (Beginner, Intermediate, or Advanced), not all three."""
    if not title or not abstract:
        return "We need both a title and an abstract to do this."

    level_guidance = GITHUB_PLAN_LEVEL_GUIDANCE.get(
        level, GITHUB_PLAN_LEVEL_GUIDANCE["Beginner"]
    )

    instructions = (
        f"Create a GitHub project plan at the {level} level only. "
        f"{level_guidance} Keep it short, simple, and practical, with "
        "no buzzwords. Reply using exactly these eleven section "
        "headings, in this exact order, each followed by a colon. Do "
        "not skip any section, and do not describe any other level:\n\n"
        "GitHub Project Title: a short, clear repository name\n"
        f"Level: {level}\n"
        "Short Project Description: 1-2 sentences for the repo description\n"
        "Why This Project Fits the Paper: a short reason this project "
        "makes sense for this specific paper\n"
        "Folder Structure: a simple suggested folder layout\n"
        "README Outline: a short list of sections a README should have\n"
        "Dataset: a dataset that could be used\n"
        "Steps to Build: 3-5 short steps to get started\n"
        "Evaluation Metrics: how to check if it works well\n"
        "Future Improvements: 2-3 ideas to extend the project later\n"
        "Resume Bullet: one short sentence to describe this project on a resume"
    )
    return _ask_openai_about_paper(title, abstract, instructions, max_tokens=650)


# Separate from GITHUB_PLAN_LEVEL_GUIDANCE: a project idea and a
# GitHub repo plan emphasize different things, even at the same level.
PROJECT_IDEA_LEVEL_GUIDANCE = {
    "Beginner": "Keep this a simple, student-friendly project that's realistic to finish.",
    "Intermediate": (
        "Make this a more complete app, ML, NLP, or data pipeline "
        "project - more than a toy example, but still doable."
    ),
    "Advanced": (
        "Make this feel research-level or industry-level, closer to "
        "what the original paper did."
    ),
}


def generate_project_idea_by_level(title, abstract, level):
    """Generates only the given level (Beginner, Intermediate, or Advanced), not all three."""
    if not title or not abstract:
        return "We need both a title and an abstract to do this."

    level_guidance = PROJECT_IDEA_LEVEL_GUIDANCE.get(
        level, PROJECT_IDEA_LEVEL_GUIDANCE["Beginner"]
    )

    instructions = (
        f"Suggest one project idea based on this paper, at the {level} "
        f"level only. {level_guidance} Keep it short, simple, and "
        "human, with no buzzwords. Reply using exactly these nine "
        "section headings, in this exact order, each followed by a "
        "colon. Do not skip any section, and do not describe any "
        "other level:\n\n"
        "Project Title: a short, clear name for the project\n"
        f"Level: {level}\n"
        "Project Idea: 2-3 sentences describing the project\n"
        "Why this idea fits the paper: a short reason this project "
        "makes sense for this specific paper\n"
        "Dataset Suggestion: a dataset that could be used\n"
        "Tech Stack: simple tools or libraries to build it with\n"
        "Build Steps: 3-5 short steps to get started\n"
        "Evaluation Metrics: how to check if the project works well\n"
        "Resume Bullet: one short sentence to describe this project on a resume"
    )
    return _ask_openai_about_paper(title, abstract, instructions, max_tokens=600)


def improve_user_project_idea(title, abstract, user_idea):
    """Improves a project idea, whether it's the app's generated idea, edited, or written by the user."""
    if not title or not abstract:
        return "We need both a title and an abstract to do this."

    if not user_idea or not user_idea.strip():
        return "Please write or generate an idea first."

    instructions = (
        f'Here is a project idea: "{user_idea.strip()}". Use the paper '
        "above to make this idea stronger and more specific. Keep it "
        "short, simple, and human, with no buzzwords. Use exactly "
        "these nine labeled sections:\n"
        "Improved Project Idea: a clearer, stronger version of the idea\n"
        "What is already good: parts of the idea that already work well\n"
        "What to improve: parts that should change, and why\n"
        "Dataset Suggestion: a dataset that could be used\n"
        "Tech Stack: simple tools or libraries to build it with\n"
        "Build Steps: 3-5 short steps to get started\n"
        "Evaluation Metrics: how to check if the project works well\n"
        "Resume Bullet: one short sentence to describe this project on a resume\n"
        "Final Recommendation: one short, clear recommendation"
    )
    return _ask_openai_about_paper(title, abstract, instructions, max_tokens=600)


def generate_paper_fit_score(title, abstract):
    """
    Returns a dict like:
        {"reading_fit": 8, "research_fit": 7, "project_fit": 9,
         "difficulty": "Intermediate", "best_for": "Build",
         "reason": "...", "skills_needed": ["Python", "..."]}
    Falls back to the raw text reply if it isn't valid JSON.
    """
    if not title or not abstract:
        return "We need both a title and an abstract to do this."

    prompt = (
        f"Paper title: {title}\nAbstract: {abstract}\n\n"
        "Score how good a fit this paper is for a student, in simple "
        "terms. Reply with ONLY valid JSON, no extra text, in exactly "
        "this shape:\n"
        "{\n"
        '  "reading_fit": 8,\n'
        '  "research_fit": 7,\n'
        '  "project_fit": 9,\n'
        '  "difficulty": "Intermediate",\n'
        '  "best_for": "Build",\n'
        '  "reason": "one short, simple sentence explaining the scores",\n'
        '  "skills_needed": ["skill1", "skill2", "skill3"]\n'
        "}\n"
        "Each *_fit score must be a whole number from 1 to 10. "
        "difficulty must be exactly Beginner, Intermediate, or Advanced. "
        "best_for must be exactly Read, Research, Build, or Full Guide. "
        "Keep reason and skills_needed short and practical."
    )

    return _call_openai_json(prompt, max_tokens=300)


def _describe_paper_for_comparison(paper):
    return (
        f"Title: {paper.get('title', '')}\n"
        f"Authors: {paper.get('authors', '')}\n"
        f"Year: {paper.get('year', '')}\n"
        f"Source: {paper.get('source', '')}\n"
        f"Summary: {paper.get('short_summary', '')}"
    )


def compare_papers(paper1, paper2):
    """
    Returns a dict matching this shape, so app.py can render it as tables:
        {
          "paper_comparison": {
            "main_topic": {"paper1": "...", "paper2": "..."},
            "method_or_approach": {"paper1": "...", "paper2": "..."},
            "strength": {"paper1": "...", "paper2": "..."},
            "limitation": {"paper1": "...", "paper2": "..."},
            "difficulty": {"paper1": "...", "paper2": "..."},
            "project_potential": {"paper1": "...", "paper2": "..."},
            "best_use": {"paper1": "...", "paper2": "..."}
          },
          "recommendation": {
            "better_for_reading": "...",
            "better_for_research": "...",
            "better_for_project": "...",
            "better_for_resume": "...",
            "final_recommendation": "..."
          }
        }
    Falls back to the raw text reply if it isn't valid JSON.
    """
    if not paper1 or not paper2:
        return "We need two papers to compare."

    prompt = (
        "Paper 1:\n" + _describe_paper_for_comparison(paper1) + "\n\n"
        "Paper 2:\n" + _describe_paper_for_comparison(paper2) + "\n\n"
        "Compare these two papers for a student deciding what to do "
        "next. Keep each answer short, simple, and human, with no "
        "buzzwords. Reply with ONLY valid JSON, no extra text, in "
        "exactly this shape:\n"
        "{\n"
        '  "paper_comparison": {\n'
        '    "main_topic": {"paper1": "...", "paper2": "..."},\n'
        '    "method_or_approach": {"paper1": "...", "paper2": "..."},\n'
        '    "strength": {"paper1": "...", "paper2": "..."},\n'
        '    "limitation": {"paper1": "...", "paper2": "..."},\n'
        '    "difficulty": {"paper1": "...", "paper2": "..."},\n'
        '    "project_potential": {"paper1": "...", "paper2": "..."},\n'
        '    "best_use": {"paper1": "...", "paper2": "..."}\n'
        "  },\n"
        '  "recommendation": {\n'
        '    "better_for_reading": "...",\n'
        '    "better_for_research": "...",\n'
        '    "better_for_project": "...",\n'
        '    "better_for_resume": "...",\n'
        '    "final_recommendation": "..."\n'
        "  }\n"
        "}"
    )

    return _call_openai_json(prompt, max_tokens=800)

# PaperTrail Study Tool

PaperTrail is a study tool for working with research papers.

I built this because finding papers is not the hard part anymore. The harder part is understanding what the paper is saying, deciding whether it is useful, and figuring out what you can do with it next.

PaperTrail helps with that process. It lets users search papers, save useful ones, compare papers, take notes, and turn a paper into a reading plan, research direction, or project idea.

## Live App

https://papertrail-study-tool.streamlit.app/

## What this project does

PaperTrail helps users:

* Search research papers from arXiv and Semantic Scholar
* Open paper links and PDFs when available
* Save papers they want to come back to
* Add notes for saved papers
* Compare two papers before deciding which one to read or use
* Get a simple explanation of a paper
* Find what skills or terms they should know before reading
* Create a reading plan for a selected paper
* Turn a paper into beginner, intermediate, or advanced project ideas
* Generate a GitHub-style project plan from a paper
* Download summaries, plans, and comparisons as TXT or PDF files

## Why I built it

When students or beginners search for research papers, they often stop after finding a few links. But after that, common questions come up:

* Which paper should I read first?
* Is this paper too difficult for me right now?
* What should I focus on while reading?
* Can this paper become a project?
* What dataset, tools, or steps would I need?
* How can I compare two papers before choosing one?

PaperTrail is built around those questions. The goal is not only to recommend papers, but to help users understand and use them.

## Main features

### Paper search

Users can search by topic, paper title, or author name. The app uses both arXiv and Semantic Scholar so the results are not limited to one source.

### Saved papers

Users can save papers, add notes, and come back to them later. Saved papers can also be downloaded for reference.

### Paper comparison

Users can select two papers and compare them. This helps when someone is trying to decide which paper is better for reading, research, or building a project.

### Reading help

For a selected paper, the app can create a simple explanation, identify important terms, and suggest what to read first.

### Project planning

The app can turn a paper into project ideas at three levels:

* Beginner
* Intermediate
* Advanced

Users can use the generated idea as it is, or edit it and improve it based on their own direction.

### GitHub project plan

For users who want to build a portfolio project, the app can generate a project plan with folder structure, dataset suggestion, build steps, evaluation ideas, and a resume bullet.

## Tech used

* Python
* Streamlit
* OpenAI API
* Semantic Scholar API
* arXiv API
* pandas
* fpdf2
* python-dotenv
* GitHub
* Streamlit Community Cloud

## How to run locally

Clone the repository:

```bash
git clone https://github.com/ManaliRathod9/papertrail-study-tool.git
```

Go into the project folder:

```bash
cd papertrail-study-tool
```

Install the required packages:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project folder:

```env
OPENAI_API_KEY=your_openai_key_here
SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_key_here
```

Run the app:

```bash
streamlit run app.py
```

## Notes

The `.env` file is not included in this repository because it contains private API keys. For deployment, the keys should be added through Streamlit secrets.

## Future improvements

Some things I would like to improve later:

* Add more paper sources
* Add better filtering by field, year, and difficulty
* Add citation export
* Save user history with login
* Improve paper ranking based on user goals
* Add more detailed project templates

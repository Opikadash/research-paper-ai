# Research AI Agent

An AI-powered research assistant that can explore research topics, analyze scientific papers, generate new research content, produce LaTeX PDFs, and perform plagiarism checks, with optional methodology flowcharts. Designed for fields like physics, computer science, mathematics, and cryptography.

## Features

Research Paper Discovery

Search for recent papers from arXiv.

Integrate IEEE Xplore for more coverage.

PDF Analysis

Upload PDFs to extract text for analysis.

AI-Assisted Paper Generation

Generate research papers based on existing literature.

Produce LaTeX PDFs, including abstracts, full text, and optional methodology flowcharts.

Methodology Flowcharts

Automatically generate a visual flowchart from the paper’s methodology.

Plagiarism Detection

Check generated papers or uploaded content for plagiarism.

Display results in chat and optionally generate a detailed report.

Interactive Chat Interface

Streamlit-based chat interface for conversational research guidance.

## Tech Stack

Backend

Python 3.10+

LangChain
 / LangGraph

Google Gemini API

PDF Handling

PyPDF2 for PDF text extraction

Tectonic for LaTeX PDF compilation

Frontend

Streamlit

Graphviz
 for flowcharts

Other Tools

Plagiarism detection (custom or via APIs)

Environment variable management with python-dotenv

## Installation

Clone the repository

git clone https://github.com/Opikadash/research-ai-agent.git
cd research-ai-agent

Create a virtual environment

python -m venv .venv
source .venv/bin/activate   # Linux / macOS
.venv\Scripts\activate      # Windows

Install dependencies

pip install -r requirements.txt

Install Tectonic (for LaTeX PDF generation)

Linux/macOS: brew install tectonic or sudo apt install tectonic

Windows: Download from Tectonic releases

Set environment variables

cp .env.example .env
### Add your Google API key in .env
## Usage

Start the Streamlit app

streamlit run frontend.py

Use the chat interface to:

Explore a research topic.

Search and summarize papers from arXiv.

Request the AI to generate a research paper.

Display methodology flowcharts.

Check for plagiarism in generated or uploaded papers.

Generate and download LaTeX PDF of the research paper.

Upload PDFs for analysis

Extract text automatically.

Run optional plagiarism checks.

Generate LaTeX PDF

Include optional methodology flowcharts.

Download the generated PDF directly from the interface.

## Example Workflow

Enter a research topic (e.g., AI Theraphist).

The AI searches for recent papers and summarizes key points.

Optionally, upload a PDF for analysis.

The AI generates a draft research paper.

Methodology steps are extracted, producing a flowchart.

Plagiarism check is performed in chat or via a separate report.

Render the paper to a LaTeX PDF, optionally including flowcharts.

Download the PDF for submission or further editing.


## Contributing

Contributions are welcome!

Fork the repo

Create a new branch (git checkout -b feature-name)

Make your changes

Submit a pull request

Please follow PEP8 standards and document any new tools or features.

## License

MIT License © 2026
See LICENSE

## Future Improvements

Integrate IEEE Xplore and Springer for broader research access.

Support multi-language papers.

Add advanced NLP summarization for large PDFs.

Generate interactive flowcharts for each section of the paper.

Add citation management and reference formatting

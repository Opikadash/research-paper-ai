# frontend.py
import streamlit as st
from pathlib import Path
import logging
import os
from dotenv import load_dotenv
from graphviz import Digraph
from ai_researcher2 import INITIAL_PROMPT, graph, config
from langchain_core.messages import AIMessage

# Tools
from arxiv_tool import paper_search
from read_pdf import read_pdf
from write_pdf import render_latex_pdf
from plagiarism_tool import plagiarism_check

# -------------------------------
# Load API keys
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# -------------------------------
# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------
# Streamlit config
st.set_page_config(page_title="Research AI Agent", page_icon="📄")
st.title("📄 Research AI Agent Dashboard")

# -------------------------------
# Session State
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pdf_path" not in st.session_state:
    st.session_state.pdf_path = None
if "last_paper_text" not in st.session_state:
    st.session_state.last_paper_text = ""
if "method_steps" not in st.session_state:
    st.session_state.method_steps = []
if "plagiarism_result" not in st.session_state:
    st.session_state.plagiarism_result = None

# -------------------------------
# Flowchart generation function
def generate_flowchart(method_steps, topic="Research Methodology"):
    dot = Digraph(comment=f"{topic} Flowchart")
    for i, step in enumerate(method_steps, 1):
        dot.node(f"Step{i}", step)
    for i in range(1, len(method_steps)):
        dot.edge(f"Step{i}", f"Step{i+1}")
    return dot

# -------------------------------
# Chat interface
user_input = st.chat_input("Enter research topic or command:")

if user_input:
    logger.info(f"User input: {user_input}")
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    chat_input = {"messages": [{"role": "system", "content": INITIAL_PROMPT}] + st.session_state.chat_history}
    full_response = ""
    flowchart_generated = False

    for s in graph.stream(chat_input, config, stream_mode="values"):
        message = s["messages"][-1]

        # Log tool calls
        if getattr(message, "tool_calls", None):
            for tool_call in message.tool_calls:
                logger.info(f"Tool call: {tool_call['name']}")

                # Plagiarism tool: only display in chat
                if tool_call["name"] == "plagiarism_check":
                    result = tool_call["arguments"]
                    st.warning(f"Plagiarism Check Result:\nScore: {result['max_similarity_score']}%\n"
                               f"Plagiarism Detected: {result['plagiarism_detected']}")

        # Agent response
        if isinstance(message, AIMessage) and message.content:
            text_content = str(message.content)
            full_response += text_content + " "
            st.chat_message("assistant").write(full_response)

            # Detect methodology steps for flowchart
            if "methodology steps:" in text_content.lower() or "research methodology" in text_content.lower():
                lines = text_content.split("\n")
                method_steps = [line.strip("-•0123456789. ") for line in lines if line.strip()]
                if method_steps:
                    flowchart_generated = True
                    st.session_state.method_steps = method_steps

    # Save final response
    if full_response:
        st.session_state.chat_history.append({"role": "assistant", "content": full_response})

    # Display flowchart if detected
    if flowchart_generated and method_steps:
        st.subheader("🗂 Methodology Flowchart")
        dot = generate_flowchart(method_steps, topic=user_input)
        st.graphviz_chart(dot)
    else:
        st.info("No methodology steps detected. Ask the agent to summarize the methodology explicitly for a flowchart.")

# -------------------------------
# Upload PDF for analysis
st.subheader("Upload PDF for Analysis")
uploaded_file = st.file_uploader("Choose a PDF", type="pdf")
if uploaded_file:
    pdf_path = Path(f"temp_uploaded.pdf")
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.read())
    st.session_state.pdf_path = pdf_path
    paper_text = read_pdf(str(pdf_path))
    st.session_state.last_paper_text = paper_text
    st.success("PDF loaded and text extracted!")

# -------------------------------
# Plagiarism Check Button
st.subheader("Plagiarism Check")
if st.session_state.last_paper_text:
    if st.button("Run Plagiarism Check"):
        result = plagiarism_check(st.session_state.last_paper_text)
        st.session_state.plagiarism_result = result
        st.warning(f"Plagiarism Check Result:\nScore: {result['max_similarity_score']}%\n"
                   f"Plagiarism Detected: {result['plagiarism_detected']}")
else:
    st.info("Upload a PDF first to run plagiarism check.")

# -------------------------------
# Generate LaTeX PDF
st.subheader("Generate LaTeX PDF")
if st.button("Generate LaTeX PDF from last paper"):
    if st.session_state.last_paper_text:
        # Optionally include methodology flowchart in PDF
        method_steps = st.session_state.method_steps
        latex_content = st.session_state.last_paper_text

        if method_steps:
            latex_flowchart = "\\begin{figure}[h]\n\\centering\n\\begin{tikzpicture}[node distance=1.5cm]\n"
            for i, step in enumerate(method_steps, 1):
                latex_flowchart += f"\\node (Step{i}) {{{step}}};\n"
                if i > 1:
                    latex_flowchart += f"\\draw[->] (Step{i-1}) -- (Step{i});\n"
            latex_flowchart += "\\end{tikzpicture}\n\\caption{Methodology Flowchart}\n\\end{figure}\n"
            latex_content += "\n" + latex_flowchart

        pdf_path = render_latex_pdf(latex_content)
        st.session_state.pdf_path = pdf_path
        st.success(f"LaTeX PDF generated: {pdf_path}")
        with open(pdf_path, "rb") as f:
            st.download_button("📥 Download PDF", f, file_name=pdf_path.name)
    else:
        st.warning("No paper text available for PDF generation.")

# frontend.py
import streamlit as st
from pathlib import Path
import logging
import os
import json
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
if "uploaded_text" not in st.session_state:
    st.session_state.uploaded_text = ""
if "paper_format" not in st.session_state:
    st.session_state.paper_format = "generic"

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
# Parse methodology steps from agent response
def parse_methodology_steps(text):
    """Parse METHODOLOGY_STEPS from agent response"""
    method_steps = []
    
    # Check for the new METHODOLOGY_STEPS format
    if "METHODOLOGY_STEPS:" in text:
        lines = text.split("METHODOLOGY_STEPS:")[1].split("\n")
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-") or line.startswith("•")):
                # Clean up the step
                step = line.lstrip("0123456789.-•) ").strip()
                if step and len(step) > 3:
                    method_steps.append(step)
    
    # Fallback to old method if no METHODOLOGY_STEPS found
    if not method_steps:
        if "methodology steps:" in text.lower() or "research methodology" in text.lower():
            lines = text.split("\n")
            for line in lines:
                line = line.strip("-•0123456789. ")
                if line and len(line) > 10:
                    method_steps.append(line)
    
    return method_steps

# -------------------------------
# Sidebar for format selection and research from attachment
st.sidebar.title("⚙️ Settings")

# Paper format selection
st.sidebar.subheader("Paper Format")
paper_format = st.sidebar.radio(
    "Select output format:",
    ["generic", "IEEE", "arXiv"],
    index=["generic", "IEEE", "arXiv"].index(st.session_state.paper_format)
)
st.session_state.paper_format = paper_format

# Upload PDF for research direction
st.sidebar.subheader("📎 Research from Attachment")
use_attachment = st.sidebar.checkbox("Use uploaded PDF for research direction", value=False)

uploaded_file_sidebar = st.sidebar.file_uploader("Upload PDF for research area", type="pdf")

if uploaded_file_sidebar:
    pdf_path = Path(f"temp_uploaded.pdf")
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file_sidebar.read())
    st.session_state.pdf_path = pdf_path
    paper_text = read_pdf(str(pdf_path))
    st.session_state.uploaded_text = paper_text
    st.sidebar.success("PDF uploaded for research direction!")

# -------------------------------
# Main chat interface
st.subheader("💬 Research Chat")

user_input = st.chat_input("Enter research topic or command:")

if user_input:
    logger.info(f"User input: {user_input}")
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # If using attachment for research, append the text to the prompt
    system_prompt = INITIAL_PROMPT
    if use_attachment and st.session_state.uploaded_text:
        system_prompt += f"\n\nIMPORTANT - User has uploaded a reference document. Use the following text to understand the research area:\n\n{str(st.session_state.uploaded_text)[:2000]}"

    chat_input = {"messages": [{"role": "system", "content": system_prompt}] + st.session_state.chat_history}
    full_response = ""
    flowchart_generated = False
    method_steps = []

    for s in graph.stream(chat_input, config, stream_mode="values"):
        message = s["messages"][-1]

        # Log tool calls
        if getattr(message, "tool_calls", None):
            for tool_call in message.tool_calls:
                logger.info(f"Tool call: {tool_call['name']}")

                # Plagiarism tool: save result for later use
                if tool_call["name"] == "plagiarism_check":
                    # Note: tool_call["arguments"] contains the input, not the result
                    # The result will be in the next message content
                    pass

        # Agent response
        if isinstance(message, AIMessage) and message.content:
            text_content = str(message.content)
            full_response += text_content + " "
            st.chat_message("assistant").write(text_content)
            
            # Try to parse plagiarism check result from response content
            if "plagiarism" in text_content.lower() or "similarity" in text_content.lower():
                # Look for similarity score in the response
                import re
                score_match = re.search(r'(\d+(?:\.\d+)?)\s*%', text_content)
                if score_match:
                    score = float(score_match.group(1))
                    plagiarism_detected = score > 30
                    st.session_state.plagiarism_result = {
                        "max_similarity_score": score,
                        "plagiarism_detected": plagiarism_detected
                    }
                    st.warning(f"Plagiarism Check Result:\nScore: {score}%\nPlagiarism Detected: {plagiarism_detected}")

            # Detect methodology steps for flowchart
            detected_steps = parse_methodology_steps(text_content)
            if detected_steps:
                method_steps = detected_steps
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
        st.info("💡 Tip: Ask the agent to explicitly list methodology steps for a flowchart visualization.")

# -------------------------------
# Plagiarism Check Section
st.divider()
st.subheader("🔍 Plagiarism Check")

col1, col2 = st.columns([3, 1])

with col1:
    if st.session_state.last_paper_text:
        if st.button("Run Plagiarism Check"):
            result = plagiarism_check(st.session_state.last_paper_text)
            st.session_state.plagiarism_result = result
            st.warning(f"Plagiarism Check Result:\nScore: {result.get('max_similarity_score', 0)}%\n"
                       f"Plagiarism Detected: {result.get('plagiarism_detected', False)}")
    else:
        st.info("Upload a PDF below to run plagiarism check.")

with col2:
    # Download button for plagiarism report
    if st.session_state.plagiarism_result:
        # Create plagiarism report as JSON
        report = {
            "plagiarism_check_result": st.session_state.plagiarism_result,
            "timestamp": str(Path().absolute())
        }
        report_json = json.dumps(report, indent=2)
        st.download_button(
            label="📥 Download Report",
            data=report_json,
            file_name="plagiarism_report.json",
            mime="application/json"
        )

# -------------------------------
# Upload PDF for analysis
st.divider()
st.subheader("📄 Upload PDF for Analysis")

uploaded_file = st.file_uploader("Choose a PDF to analyze", type="pdf")
if uploaded_file:
    pdf_path = Path(f"temp_uploaded.pdf")
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.read())
    st.session_state.pdf_path = pdf_path
    paper_text = read_pdf(str(pdf_path))
    st.session_state.last_paper_text = paper_text
    st.success("PDF loaded and text extracted!")

# -------------------------------
# Generate LaTeX PDF
st.divider()
st.subheader("📑 Generate LaTeX PDF")

# Show current format
st.info(f"Current format: **{st.session_state.paper_format.upper()}**")

if st.button("Generate LaTeX PDF from last paper"):
    if st.session_state.last_paper_text:
        # Include methodology flowchart in PDF
        method_steps = st.session_state.method_steps
        latex_content = st.session_state.last_paper_text

        # Generate flowchart image if steps exist
        if method_steps:
            latex_flowchart = "\\begin{figure}[h]\n\\centering\n\\begin{tikzpicture}[node distance=1.5cm]\n"
            for i, step in enumerate(method_steps, 1):
                latex_flowchart += f"\\node (Step{i}) {{{step}}};\n"
                if i > 1:
                    latex_flowchart += f"\\draw[->] (Step{i-1}) -- (Step{i});\n"
            latex_flowchart += "\\end{tikzpicture}\n\\caption{Methodology Flowchart}\n\\end{figure}\n"
            latex_content += "\n" + latex_flowchart

        # Generate PDF with selected format
        pdf_path = render_latex_pdf(latex_content, paper_format=st.session_state.paper_format)
        st.session_state.pdf_path = pdf_path
        st.success(f"LaTeX PDF generated in {st.session_state.paper_format.upper()} format: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            # Dynamic filename based on format
            format_suffix = f"_{st.session_state.paper_format}" if st.session_state.paper_format != "generic" else ""
            st.download_button(
                label=f"📥 Download PDF ({st.session_state.paper_format.upper()})", 
                data=f, 
                file_name=f"research_paper{format_suffix}.pdf"
            )
    else:
        st.warning("No paper text available for PDF generation. Upload a PDF first.")

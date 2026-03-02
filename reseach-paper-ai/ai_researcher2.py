# Step1: Define state
from typing_extensions import TypedDict
from typing import Annotated, Literal
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import os

# Step2: Load tools
from arxiv_tool import paper_search  # unified arXiv + IEEE tool
from read_pdf import read_pdf
from write_pdf import render_latex_pdf
from langgraph.prebuilt import ToolNode


tools = [paper_search, read_pdf, render_latex_pdf]
tool_node = ToolNode(tools)

load_dotenv()

class State(TypedDict):
    messages: Annotated[list, add_messages]

# Step3: Setup LLM
from langchain_google_genai import ChatGoogleGenerativeAI

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=os.getenv("GOOGLE_API_KEY")
).bind_tools(tools)

# Step4: Setup graph
from langgraph.graph import END, START, StateGraph

def call_model(state: State):
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}

def should_continue(state: State) -> Literal["tools", END]:
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END

workflow = StateGraph(State)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()
config = {"configurable": {"thread_id": 222222}}

graph = workflow.compile(checkpointer=checkpointer)

# Step5: INITIAL PROMPT
INITIAL_PROMPT = """
You are an expert researcher in the fields of physics, mathematics,
computer science, quantitative biology, quantitative finance, statistics,
electrical engineering and systems science, and economics.

You are going to analyze recent research papers in one of these fields in
order to identify promising new research directions and then write a new
research paper. For research information or getting papers, ALWAYS use arxiv.org
and ieee.org. You will use the tools provided to search for papers, read them,
and write a new paper based on the ideas you find.

To start with, have a conversation with me in order to figure out what topic
to research. Then tell me about some recently published papers with that topic.
Once I've decided which paper I'm interested in, go ahead and read it in order
to understand the research that was done and the outcomes.

Pay particular attention to the ideas for future research and think carefully
about them, then come up with a few ideas. Let me know what they are and I'll
decide what one you should write a paper about.

Finally, I'll ask you to go ahead and write the paper. Make sure that you
include mathematical equations in the paper. Once it's complete, you should
render it as a LaTeX PDF. Make sure that TEX file is correct and there is no error in it so that PDF is easily exported. When you give papers references, always attach the pdf links to the paper. 
"""

# Step6: Helper to stream responses
def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]
        content_preview = (message.content[:200] + '...') if message.content else ""
        print(f"Message received: {content_preview}")
        message.pretty_print()

# Step7: Example interactive loop
"""
while True:
    user_input = input("User: ")
    if user_input:
        messages = [
            {"role": "system", "content": INITIAL_PROMPT},
            {"role": "user", "content": user_input}
        ]
        input_data = {"messages": messages}
        print_stream(graph.stream(input_data, config, stream_mode="values"))
"""

"""Test script to run the research paper generation workflow"""
import sys
sys.path.insert(0, '.')

from ai_researcher2 import graph, INITIAL_PROMPT, config, print_stream

def run_research_flow():
    # Step 1: Start conversation about the topic
    user_input = "Post-Quantum Cryptography: Preparing for the Quantum Threat"
    
    messages = [
        {"role": "system", "content": INITIAL_PROMPT},
        {"role": "user", "content": f"I want to research: {user_input}. Please search for relevant papers and tell me about them."}
    ]
    
    print(f"\n=== Step 1: Searching for papers on '{user_input}' ===\n")
    for s in graph.stream({"messages": messages}, config, stream_mode="values"):
        message = s["messages"][-1]
        if hasattr(message, 'content') and message.content:
            print(f"Assistant: {message.content[:500]}...")
        if hasattr(message, 'tool_calls') and message.tool_calls:
            print(f"Tool calls: {[tc['name'] for tc in message.tool_calls]}")
    
    # Step 2: Ask to select a paper and write the research paper
    print("\n=== Step 2: Asking AI to write research paper ===\n")
    messages.append({"role": "user", "content": "Please select the most relevant paper, read it, and then write a new research paper based on the ideas. Finally, render it as a LaTeX PDF."})
    
    for s in graph.stream({"messages": messages}, config, stream_mode="values"):
        message = s["messages"][-1]
        if hasattr(message, 'content') and message.content:
            content = message.content
            print(f"Assistant: {content[:300]}...")
            if "PDF" in content or "pdf" in content:
                print("\n*** PDF Generated! ***\n")
        if hasattr(message, 'tool_calls') and message.tool_calls:
            print(f"Tool calls: {[tc['name'] for tc in message.tool_calls]}")

if __name__ == "__main__":
    run_research_flow()

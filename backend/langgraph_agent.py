"""
STEP 6: LangGraph Agent Loop
Building agent that executes tools automatically in a loop.

Components to build:
1. Imports
2. AgentState (what data persists)
3. Tools (get_weather, calculator)
4. LLM with tools
5. chat_node (calls LLM)
6. tool_node (executes tools)
7. Routing logic (continue or end?)
8. Build graph
9. Run agent
"""

# ============================================
# COMPONENT 1: IMPORTS
# ============================================
# What we need:
# - TypedDict: structure for state
# - operator.add: for message accumulation
# - ChatGroq: LLM from Groq
# - @tool: decorator to define tools
# - Messages: HumanMessage, AIMessage, ToolMessage
# - StateGraph, END: graph structure

from typing import TypedDict, Annotated
import operator
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
import os
import requests

load_dotenv()

print("✓ Imports loaded")

# ============================================
# COMPONENT 2: AGENTSTATE
# ============================================
# What is AgentState?
# Blueprint for what data persists through agent loop
# messages = list of all conversation turns (accumulates)
# Annotated[list, operator.add] = when node adds message, append not replace

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]

print("✓ AgentState defined")

# ============================================
# COMPONENT 3: TOOLS
# ============================================
# What are tools?
# Functions LLM can call. @tool decorator tells LangChain this is callable.
# LLM reads docstring + type hints to understand what tool does.

@tool
def get_weather(city: str, state: str) -> str:
    """Get current weather for a city.

    Args:
        city: City name (e.g., Irving)
        state: State (e.g., Texas, TX)

    Returns: Weather description and temperature
    """
    try:
        api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        if not api_key:
            return "Error: OPENWEATHERMAP_API_KEY not set"

        url = f"https://api.openweathermap.org/data/2.5/weather?q={city},{state},US&appid={api_key}&units=metric"
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200:
            return f"Error: {data.get('message', 'Unknown error')}"

        temp = data['main']['temp']
        condition = data['weather'][0]['description']
        humidity = data['main']['humidity']

        return f"Weather in {city}, {state}: {condition.capitalize()}. Temperature: {temp}°C. Humidity: {humidity}%"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression.

    Args:
        expression: Math expression (e.g., "5 + 3", "10 * 2")

    Returns: Result of calculation
    """
    try:
        result = eval(expression)
        return f"Result: {result}"
    except:
        return "Error: Invalid expression"

# List all tools
tools = [get_weather, calculator]

print("✓ Tools defined (get_weather, calculator)")

# ============================================
# COMPONENT 4: LLM WITH TOOLS
# ============================================
# Create LLM instance
llm = ChatGroq(
    model="qwen/qwen3.6-27b",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
    max_tokens=2000,
)

# Bind tools to LLM
# This tells LLM: "You can call these tools. Here's what they do."
llm_with_tools = llm.bind_tools(tools)

print("✓ LLM created and tools bound")

# ============================================
# COMPONENT 5: CHAT NODE
# ============================================
# What happens in chat_node?
# 1. Takes current state (all messages so far)
# 2. Calls LLM with those messages
# 3. LLM reads tools + history, decides: call tool or respond?
# 4. Return LLM response added to state
#
# Loop step: [CHAT NODE] → LLM responds (maybe with tool_calls)

def chat_node(state: AgentState):
    """
    Call LLM. LLM sees full conversation history.
    LLM decides: which tool (if any) should I call?
    """
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    # Add response to message history
    return {"messages": [response]}

print("✓ chat_node defined")

# ============================================
# COMPONENT 6: TOOL NODE
# ============================================
# What happens in tool_node?
# 1. Take LLM response from state
# 2. Extract tool_calls (if any)
# 3. For each tool call: execute it
# 4. Wrap results in ToolMessage
# 5. Return results added to state
#
# Loop step: [TOOL NODE] → execute tool → return result

def tool_node(state: AgentState):
    """
    Execute tools. Extract tool_calls from LLM response.
    Run each tool. Return results.
    """
    # Get last message (the LLM response with tool_calls)
    last_message = state["messages"][-1]

    # Create tool lookup map
    tool_map = {tool.name: tool for tool in tools}

    tool_results = []

    # Check if LLM called any tools
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # Execute the tool
            result = tool_map[tool_name].invoke(tool_args)

            # Wrap result in ToolMessage
            tool_message = ToolMessage(
                content=result,
                tool_call_id=tool_call["id"],
                name=tool_name
            )
            tool_results.append(tool_message)

    return {"messages": tool_results}

print("✓ tool_node defined")

# ============================================
# COMPONENT 7: ROUTING LOGIC
# ============================================
# What is routing?
# After tool_node executes, decide: what's next?
# - If LLM response has more tool_calls → go back to chat_node
# - If LLM response has NO tool_calls → we're done, END
#
# Why? Loop continues until agent decides no more tools needed.

def should_continue(state: AgentState):
    """
    Decision point: continue loop or stop?

    Returns:
      "chat" → call LLM again (it saw tool results)
      "end" → stop, conversation done
    """
    # Get last message
    last_message = state["messages"][-1]

    # Does it have tool calls?
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        # Yes, keep looping
        return "chat"
    else:
        # No more tools, stop
        return "end"

print("✓ Routing logic defined")

# ============================================
# COMPONENT 8: BUILD STATEGRAPH
# ============================================
# What is StateGraph?
# Container that wires nodes + edges together into runnable agent.
#
# Graph structure:
#   chat_node (LLM calls)
#     ↓
#   tool_node (execute tools)
#     ↓
#   [should_continue decision]
#     ├─→ if tool_calls exist → back to chat_node
#     └─→ if no tool_calls → END

# Create graph
graph = StateGraph(AgentState)

# Add nodes (the two main functions)
graph.add_node("chat", chat_node)
graph.add_node("tools", tool_node)

# Add edges (transitions)
# After chat, always go to tools
graph.add_edge("chat", "tools")

# After tools, decide: continue or end?
graph.add_conditional_edges(
    "tools",
    should_continue,
    {"chat": "chat", "end": END}
)

# Set entry point (where to start)
graph.set_entry_point("chat")

# Compile graph to runnable agent
agent = graph.compile()

print("✓ StateGraph built and compiled")
print("\nGraph structure:")
print("  [START]")
print("    ↓")
print("  [CHAT NODE] ← LLM calls tools or responds")
print("    ↓")
print("  [TOOL NODE] ← Execute tools")
print("    ↓")
print("  [ROUTING]")
print("    ├─→ has tool_calls? YES → back to CHAT NODE")
print("    └─→ has tool_calls? NO → END")

# ============================================
# COMPONENT 9: RUN AGENT
# ============================================
# Create initial state with user query
initial_state = {
    "messages": [HumanMessage(content="What is 1 / 0?")]
}

print("\n" + "="*60)
print("RUNNING AGENT")
print("="*60)
print("\nUser: What is 1 / 0?")
print("\nAgent executing...\n")

# Invoke agent
result = agent.invoke(initial_state)

# Show final conversation
print("="*60)
print("FINAL CONVERSATION")
print("="*60)

for i, msg in enumerate(result["messages"]):
    msg_type = type(msg).__name__
    print(f"\n[{i}] {msg_type}:")

    if hasattr(msg, 'content'):
        content = msg.content
        
        print(f"    {content}")

    if hasattr(msg, 'tool_calls') and msg.tool_calls:
        tool_names = [t['name'] for t in msg.tool_calls]
        print(f"    → Called tools: {tool_names}")

"""
LangGraph agent for chat with tool use (calculator, weather).
"""

import os
from typing import TypedDict, Annotated
import operator

from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
import requests

load_dotenv()


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]


@tool
def get_weather(city: str, state: str = "") -> str:
    """Get current weather for a city.

    Args:
        city: City name (e.g., Delhi, Delhi, London)
        state: State/country (e.g., India, Texas, UK). Optional.

    Returns: Weather description and temperature
    """
    try:
        api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        if not api_key:
            return "Error: OPENWEATHERMAP_API_KEY not set"

        if state:
            query = f"{city},{state}"
            display = f"{city}, {state}"
        else:
            query = city
            display = city

        url = f"https://api.openweathermap.org/data/2.5/weather?q={query}&appid={api_key}&units=metric"
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200:
            return f"Error: {data.get('message', 'Unknown error')}"

        temp = data['main']['temp']
        condition = data['weather'][0]['description']
        humidity = data['main']['humidity']

        return f"Weather in {display}: {condition.capitalize()}. Temperature: {temp}°C. Humidity: {humidity}%"
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


tools = [get_weather, calculator]


def create_agent():
    """Create and compile LangGraph agent."""

    llm = ChatGroq(
        model="qwen/qwen3.6-27b",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
        max_tokens=2000,
    )

    llm_with_tools = llm.bind_tools(tools)

    def chat_node(state: AgentState):
        messages = state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def tool_node(state: AgentState):
        last_message = state["messages"][-1]
        tool_map = {tool.name: tool for tool in tools}
        tool_results = []

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                result = tool_map[tool_name].invoke(tool_args)
                tool_message = ToolMessage(
                    content=result,
                    tool_call_id=tool_call["id"],
                    name=tool_name
                )
                tool_results.append(tool_message)

        return {"messages": tool_results}

    def should_continue(state: AgentState):
        last_message = state["messages"][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "chat"
        else:
            return "end"

    graph = StateGraph(AgentState)
    graph.add_node("chat", chat_node)
    graph.add_node("tools", tool_node)
    graph.add_edge("chat", "tools")
    graph.add_conditional_edges(
        "tools",
        should_continue,
        {"chat": "chat", "end": END}
    )
    graph.set_entry_point("chat")

    return graph.compile()

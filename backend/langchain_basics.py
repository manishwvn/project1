from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from dotenv import load_dotenv
import os
import requests

load_dotenv()

# Create LLM instance
llm = ChatGroq(
    model="qwen/qwen3.6-27b",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
    max_tokens=2000,
)

# prompt = PromptTemplate(
#     template="Explain this in one sentence: {topic}", input_variables=["topic"]
# )

# formatted_prompt = prompt.format(topic="machine learning")
# response = llm.invoke(formatted_prompt)
# print(response.content)
# # step 3 chains

# chain = prompt | llm
# response = chain.invoke({"topic": "machine learning"})
# print(response.content)

# # Step 4: Memory - conversation history
# history = []

# chat_prompt = ChatPromptTemplate.from_messages([
#     ("system", "You are a helpful assistant. Use conversation history to answer."),
#     ("human", "{history}\n\nNew question: {input}")
# ])

# memory_chain = chat_prompt | llm

# questions = [
#     "What is machine learning?",
#     "Can you explain it in simple terms?",
#     "What are some common applications?"
# ]

# for question in questions:
#     print(f"\nUser: {question}")

#     history_text = "\n".join(history) if history else "No previous messages"

#     response = memory_chain.invoke(
#         {
#             "history": history_text,
#             "input": question
#         }
#     )

#     print(f"Agent: {response.content}")

#     history.append(f"User: {question}")
#     history.append(f"Agent: {response.content}")


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        result = eval(expression)
        return f"Result: {result}"
    except:
        return "Error: Invalid expression"

@tool
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

@tool
def get_weather(city: str, state: str) -> str:
    """
    Get current weather for a city.

    Args:
        city: City name (e.g., Irving, New York)
        state: State code or name (e.g., TX, Texas, CA)

    Returns: Weather description, temperature, and conditions.
    """
    try:
        api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        country = "US"

        url = f"https://api.openweathermap.org/data/2.5/weather?q={city},{state},{country}&appid={api_key}&units=metric"

        response = requests.get(url)
        data = response.json()

        if response.status_code != 200:
            return f"Error: {data.get('message', 'Unknown error')}"

        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        condition = data['weather'][0]['description']
        humidity = data['main']['humidity']

        return f"Weather in {city}, {state}: {condition.capitalize()}. Temperature: {temp}°C (feels like {feels_like}°C). Humidity: {humidity}%"

    except Exception as e:
        return f"Error: {str(e)}"

tools = [calculator, add_numbers, get_weather]
llm_with_tools = llm.bind_tools(tools)

# Step 5: Tools - LLM decides which tool to call
response = llm_with_tools.invoke("What is the weather in Irving Texas?")
print("Tool calls (LLM decision):", response.tool_calls)
print("LLM content:", response.content)

# Manually execute tool (Step 6 LangGraph will do this in loop)
tool_map = {tool.name: tool for tool in tools}

if response.tool_calls:
    for call in response.tool_calls:
        tool_name = call['name']
        tool_args = call['args']
        tool_obj = tool_map[tool_name]
        result = tool_obj.invoke(tool_args)
        print(f"Tool executed: {tool_name}({tool_args}) = {result}")
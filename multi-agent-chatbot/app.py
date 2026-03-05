import streamlit as st
import requests as req
import math
import sqlite3
from agno.agent import Agent
from agno.team import Team
from agno.models.openrouter import OpenRouter
from agno.tools.duckduckgo import DuckDuckGoTools

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(page_title="Multi Agent Chatbot", layout="wide")
st.title("🤖 Multi Agent Chatbot")
st.caption("Powered by Agno + OpenRouter + Tools")

# -----------------------------
# Sidebar Settings
# -----------------------------
st.sidebar.subheader("⚙️ Settings")
api_key = st.sidebar.text_input("OpenRouter API Key", type="password")
model_name = st.sidebar.text_input("Model", "stepfun/step-3.5-flash:free")
weather_api_key = st.sidebar.text_input("OpenWeather API Key (optional)", type="password")

st.sidebar.divider()
show_steps = st.sidebar.checkbox("Show Tool Calls", value=True)

st.sidebar.divider()
st.sidebar.subheader("🛠️ Enabled Tools")
st.sidebar.markdown("✅ 🔍 DuckDuckGo Search")
st.sidebar.markdown("✅ 🌤️ get_weather")
st.sidebar.markdown("✅ 🌐 fetch_url")
st.sidebar.markdown("✅ 📖 Wikipedia Search")
st.sidebar.markdown("✅ 🧮 Calculator")
st.sidebar.markdown("✅ 🗄️ Database Query")

# -----------------------------
# Tool 1 — Weather
# -----------------------------
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    if weather_api_key:
        try:
            url = "http://api.openweathermap.org/data/2.5/weather"
            params = {"q": city, "appid": weather_api_key, "units": "metric"}
            response = req.get(url, params=params)
            data = response.json()
            if response.status_code == 200:
                desc = data["weather"][0]["description"]
                temp = data["main"]["temp"]
                humidity = data["main"]["humidity"]
                wind = data["wind"]["speed"]
                return (
                    f"Weather in {city}:\n"
                    f"- Condition: {desc}\n"
                    f"- Temperature: {temp}°C\n"
                    f"- Humidity: {humidity}%\n"
                    f"- Wind Speed: {wind} m/s"
                )
            else:
                return f"Could not fetch weather: {data.get('message', 'Unknown error')}"
        except Exception as e:
            return f"Weather fetch error: {str(e)}"
    else:
        return f"No OpenWeather API key. Searching DuckDuckGo for weather in {city}."


# -----------------------------
# Tool 2 — Fetch URL
# -----------------------------
def fetch_url(url: str) -> str:
    """Fetch and return the text content of a URL."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = req.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            text = response.text[:2000]
            return f"Content from {url}:\n\n{text}"
        else:
            return f"Failed to fetch {url}. Status: {response.status_code}"
    except Exception as e:
        return f"URL fetch error: {str(e)}"


# -----------------------------
# Tool 3 — Wikipedia
# -----------------------------
def search_wikipedia(query: str) -> str:
    """Search Wikipedia and return a summary."""
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + query.replace(" ", "_")
        headers = {"User-Agent": "MultiAgentChatbot/1.0"}
        response = req.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            title = data.get("title", query)
            extract = data.get("extract", "No summary available.")
            page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
            return f"Wikipedia — {title}:\n\n{extract}\n\nURL: {page_url}"
        else:
            return f"No Wikipedia page found for '{query}'."
    except Exception as e:
        return f"Wikipedia search error: {str(e)}"


# -----------------------------
# Tool 4 — Calculator
# -----------------------------
def calculator(expression: str) -> str:
    """Safely evaluate a math expression. Example: '2 + 2', 'sqrt(16)', '10 * 5'"""
    try:
        safe_dict = {
            "sqrt": math.sqrt, "pow": math.pow, "abs": abs,
            "round": round, "pi": math.pi, "e": math.e,
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "log": math.log, "log10": math.log10,
            "floor": math.floor, "ceil": math.ceil,
        }
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        return f"Result of '{expression}' = {result}"
    except Exception as e:
        return f"Calculation error: {str(e)}"


# -----------------------------
# Tool 5 — Database Query
# -----------------------------
def query_database(sql: str) -> str:
    """Run a SQL query on a local SQLite demo database."""
    try:
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY,
                name TEXT,
                department TEXT,
                salary INTEGER
            )
        """)
        cursor.executemany("INSERT INTO employees VALUES (?, ?, ?, ?)", [
            (1, "Alice", "Engineering", 90000),
            (2, "Bob", "Marketing", 70000),
            (3, "Charlie", "Engineering", 95000),
            (4, "Diana", "HR", 65000),
            (5, "Eve", "Marketing", 72000),
        ])
        conn.commit()
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        if rows:
            header = " | ".join(columns)
            divider = "-" * len(header)
            result_rows = "\n".join([" | ".join(str(v) for v in row) for row in rows])
            return f"Query: {sql}\n\n{header}\n{divider}\n{result_rows}"
        else:
            return f"Query returned no results: {sql}"
    except Exception as e:
        return f"Database error: {str(e)}"


# -----------------------------
# Build Agents
# -----------------------------
def build_team(api_key, model_name):
    model = OpenRouter(
        id=model_name,
        api_key=api_key
    )

    researcher = Agent(
        name="Researcher",
        role=(
            "You are a researcher. Use tools to find information. "
            "You can search the web, get weather, fetch URLs, "
            "search Wikipedia, do calculations, and query a database."
        ),
        model=model,
        tools=[
            DuckDuckGoTools(),
            get_weather,
            fetch_url,
            search_wikipedia,
            calculator,
            query_database,
        ],
    )

    writer = Agent(
        name="Writer",
        role="Take research findings and write a clear, simple, well structured answer.",
        model=model,
    )

    master = Team(
        name="Master Agent",
        mode="coordinate",
        members=[researcher, writer],
        model=model,
        instructions=[
            "First ask the Researcher to gather information using the right tools.",
            "Then ask the Writer to write a clear simple answer.",
            "Finally combine both into one great response.",
        ],
    )

    return master


# -----------------------------
# Chat Interface
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and show_steps and msg.get("steps"):
            with st.expander("🔍 Agent Steps", expanded=False):
                for step in msg["steps"]:
                    st.markdown(step)
        st.write(msg["content"])

question = st.chat_input("Ask anything... weather, wiki, math, news, database...")

if question:
    if not api_key:
        st.warning("⚠️ Please add your OpenRouter API key in the sidebar.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("🤖 Agents working..."):
            try:
                master = build_team(api_key, model_name)
                response = master.run(question)

                # Extract answer properly
                if hasattr(response, "content") and response.content:
                    answer = response.content
                elif hasattr(response, "messages") and response.messages:
                    answer = "⚠️ Could not extract answer."
                    for msg_item in reversed(response.messages):
                        if hasattr(msg_item, "role") and msg_item.role == "assistant":
                            if hasattr(msg_item, "content") and msg_item.content:
                                if isinstance(msg_item.content, list):
                                    answer = " ".join([
                                        c.get("text", "") if isinstance(c, dict) else str(c)
                                        for c in msg_item.content
                                    ])
                                else:
                                    answer = str(msg_item.content)
                                break
                else:
                    answer = "⚠️ No response received from agents."

                # Extract steps
                steps_log = []
                try:
                    for msg_item in response.messages:
                        if hasattr(msg_item, "tool_calls") and msg_item.tool_calls:
                            for tool_call in msg_item.tool_calls:
                                name = tool_call.get("function", {}).get("name", "unknown")
                                steps_log.append(f"🔧 Tool called: **{name}**")
                        if hasattr(msg_item, "role") and msg_item.role == "tool":
                            steps_log.append("✅ Tool result received")
                except Exception:
                    pass

                if show_steps and steps_log:
                    with st.expander("🔍 Agent Steps", expanded=True):
                        for step in steps_log:
                            st.markdown(step)

            except Exception as e:
                answer = f"❌ Error: {str(e)}"
                steps_log = []

        st.write(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "steps": steps_log if "steps_log" in locals() else []
    })

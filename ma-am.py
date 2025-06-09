import os
import re
from dotenv import load_dotenv
from influxdb import InfluxDBClient
from langchain_community.tools import Tool
from langchain.agents import create_react_agent
from langchain.agents.agent import AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from collections import defaultdict
from datetime import datetime

# === Load environment variables ===
load_dotenv()

# === InfluxDB Config from .env ===
INFLUX_HOST = os.getenv("INFLUX_HOST")
INFLUX_PORT = int(os.getenv("INFLUX_PORT", 8086))
INFLUX_USERNAME = os.getenv("INFLUX_USERNAME")
INFLUX_PASSWORD = os.getenv("INFLUX_PASSWORD")
INFLUX_DB = os.getenv("INFLUX_DB")

client = InfluxDBClient(
    host=INFLUX_HOST,
    port=INFLUX_PORT,
    username=INFLUX_USERNAME,
    password=INFLUX_PASSWORD,
    database=INFLUX_DB
)

# === Tool: List InfluxDB Measurements ===
def list_measurements(_: str = "") -> str:
    result = client.query("SHOW MEASUREMENTS")
    measurements = [m['name'] for m in result.get_points()]
    return "Observation: \n" + "\n".join(f"- {m}" for m in measurements)

# === Tool: Query InfluxDB Measurement ===
def query_measurement(params: str) -> str:
    try:
        params = params.strip().strip("'\"")
        measurement_match = re.match(r'^\s*([^,]+)', params)
        time_match = re.search(r'time\s*=\s*([0-9]+[smhdw])', params)
        mode_match = re.search(r'mode\s*=\s*(raw|summary)', params, re.IGNORECASE)

        if not measurement_match:
            return "Observation: ❌ Invalid input format. Provide a measurement name like: 'StepsIntraday, time=7d, mode=summary'"

        measurement = measurement_match.group(1).strip()
        time_clause = f"WHERE time >= now() - {time_match.group(1)}" if time_match else ""
        mode = mode_match.group(1).lower() if mode_match else "summary"

        q = f'SELECT * FROM "{measurement}" {time_clause}'
        result = client.query(q)
        entries = list(result.get_points())
        if not entries:
            return f"Observation: ⚠️ No data found in '{measurement}'. Try expanding the time range."

        if mode == "summary":
            summary = defaultdict(lambda: defaultdict(list))  # {field: {day: [values]}}
            today = datetime.utcnow().strftime('%Y-%m-%d')

            for entry in entries:
                ts = entry.get("time")
                if not ts:
                    continue
                day = ts[:10]
                if day == today:
                    continue  # skip current day
                for key, value in entry.items():
                    if isinstance(value, (int, float)) and value is not None:
                        summary[key][day].append(value)

            output = f"📊 Summary for '{measurement}' over {time_match.group(1) if time_match else 'recent'}:\n"
            has_data = False

            for field, day_dict in summary.items():
                daily_totals = [sum(vs) for vs in day_dict.values()]
                if daily_totals:
                    has_data = True
                    mean = sum(daily_totals) / len(daily_totals)
                    output += f"- {field}: mean={mean:.2f}, min={min(daily_totals):.2f}, max={max(daily_totals):.2f}\n"
            return "Observation: " + (output.strip() if has_data else f"⚠️ All numeric fields in '{measurement}' contain only zero or missing values.")

        else:
            limit_match = re.search(r'limit\s*=\s*(\d+)', params)
            limit = int(limit_match.group(1)) if limit_match else 50
            entries = entries[:limit]
            fields = entries[0].keys()
            output = f"📄 Raw data for '{measurement}' (limit={limit}):\n\n"
            output += " | ".join(fields) + "\n"
            output += "-" * 80 + "\n"
            for row in entries:
                output += " | ".join(str(row.get(f, "")) for f in fields) + "\n"
            return "Observation: " + output.strip()

    except Exception as e:
        return f"Observation: ❌ Query error: {e}"

# === Tool: Show Field Keys for InfluxDB Measurement ===
def show_field_keys(measurement: str) -> str:
    try:
        query = f'SHOW FIELD KEYS FROM "{measurement.strip()}"'
        result = client.query(query)
        fields = [f"{r['fieldKey']} ({r['fieldType']})" for r in result.get_points()]
        return "Observation: " + (f"Fields for '{measurement}': " + ", ".join(fields) if fields else "No fields found.")
    except Exception as e:
        return f"Observation: Error retrieving field keys: {e}"

# === Tool Registration ===
tools = [
    Tool.from_function(list_measurements, "list_measurements", "Lists all measurement names in the InfluxDB database"),
    Tool.from_function(
        func=query_measurement,
        name="query_measurement",
        description=(
            "Query wearable measurement data from InfluxDB.\n"
            "By default, returns a summarized view (mean, min, max).\n"
            "Use 'mode=raw' to get raw data rows. Optional parameters: 'time', 'limit'.\n"
            "Examples:\n"
            "  StepsIntraday, time=7d\n"
            "  StepsIntraday, time=7d, mode=raw\n"
            "  StressIntraday, time=30d, limit=100, mode=raw"
        )
    ),
    Tool.from_function(show_field_keys, "show_field_keys", "Show fields for a given measurement in InfluxDB")
]

# === Load Prompt Template ===
with open("coach_prompt.txt", "r") as f:
    prompt_text = f.read()

prompt = PromptTemplate.from_template(prompt_text)

# === LLM Setup ===
model_name = os.getenv("OPENAI_MODEL", "gpt-4")
print(f"🔍 Using model: {model_name}")

llm = ChatOpenAI(
    model=model_name,
    temperature=0,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# === Agent Setup ===
agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True
)

# === Main Program ===
def extract_measurements_from_input(user_input, available_measurements):
    user_input_lower = user_input.lower()
    matches = [m for m in available_measurements if m.lower() in user_input_lower]
    return matches

def main():
    measurements_response = list_measurements("")
    available_measurements = [line.strip("- ").strip() for line in measurements_response.splitlines() if line.startswith("- ")]

    print("\n🤖 GPT Health Coach: Ready to chat about your health. Ask me anything!")
    while True:
        try:
            question = input("\nYou: ")
            if question.lower() in ["exit", "quit"]:
                print("👋 Take care!")
                break

            mentioned = extract_measurements_from_input(question, available_measurements)
            if mentioned:
                print(f"🔎 Focused on: {', '.join(mentioned)}")
                response = agent_executor.invoke({"input": question, "focus": ", ".join(mentioned)})
            else:
                response = agent_executor.invoke({"input": question})

            print("\n🤖 GPT Health Coach:", response["output"])

        except Exception as e:
            print(f"\n⚠️ Error: {e}")

if __name__ == "__main__":
    main()


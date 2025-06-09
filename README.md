# 🧠 MA-AM: Minimal Agent for Activity Monitoring

**MA-AM** (Minimal Agent for Activity Monitoring) is a lightweight, modular AI health coach built with LangChain and InfluxDB. It connects to your wearable health data and offers concise, data-driven coaching through a command-line interface.

---

## 🚀 Features

- 🧠 GPT-powered health assistant (ReAct agent)
- 📊 Integrates with InfluxDB for querying wearable data
- 🔧 Built-in tools to list, explore, and summarize measurements
- ✍️ Prompt-engineered for no-nonsense, actionable advice
- 🛠️ Simple CLI interface for local interaction

---

## 📦 Installation

```bash
git clone https://github.com/stynoo/ma-am.git
cd ma-am
poetry install
```

Create a `.env` file using the `.env.example` template:

```env
INFLUX_HOST=localhost
INFLUX_PORT=8086
INFLUX_USERNAME=your_user
INFLUX_PASSWORD=your_pass
INFLUX_DB=your_db
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o
```

---

## 🧪 Usage

Run the agent:

```bash
poetry run python ma-am.py
```

Example prompts:
```
- tell me about my steps
- how did I sleep over the last 7 days?
- what’s my average stress this month?
```

To exit: type `exit` or `quit`

---

## 🛠 Tools

The assistant has access to built-in tools:

- `list_measurements` — show all available metrics
- `query_measurement` — fetch & summarize time series
- `show_field_keys` — list fields in a measurement

---

## 🧩 Architecture

- `ma-am.py`: Entry point with CLI + agent execution
- `coach_prompt.txt`: Prompt template for agent behavior
- `pyproject.toml`: Poetry-based dependency management

---

## 📄 License

MIT License © [stynoo](https://github.com/stynoo)
---

## 🙏 Acknowledgements

This project uses data and InfluxDB setup provided by [garmin-grafana](https://github.com/arpanghosh8453/garmin-grafana) by [arpanghosh8453](https://github.com/arpanghosh8453).


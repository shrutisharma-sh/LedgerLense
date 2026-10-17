# AI Usage

- AI (Claude) helped draft the synthetic data generator, loader.py, the Streamlit UI and the agent boilerplate.
- I designed the story, schema and planted facts (including decoys), ran everything, and checked results against ANSWER_KEY.md.
- The risk-signal logic lives in Cypher queries, not Python loops. I can explain each one.
- Agent LLM: Groq (llama-3.3-70b-versatile), calling fixed Cypher tools.
- All data is synthetic. No real or personal data.
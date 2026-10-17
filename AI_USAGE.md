# AI Usage

- AI (Claude) helped draft the synthetic data generator , the Streamlit UI and the boilerplate.
- I designed the story, schema and planted facts (including decoys), ran everything, and checked results against ANSWERs
- The risk-signal logic lives in Cypher queries, not Python loops. I can explain each one.
- Agent LLM: Groq (openai/gpt-oss-120b), calling fixed Cypher tools.
- All data is synthetic. No real or personal data.
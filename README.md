# LedgerLens

An agent that follows hidden relationships in a FalkorDB graph to surface risk signals in a housing society's finances.

> **Synthetic data. Risk signals, not accusations.** All people, companies and amounts are fictional. No real or personal data is used. Findings need human verification.

**Hackathon:** Graph Hacks: Context for AI Agents (FalkorDB)
**Track entered:** Track 01, Agents That Act on Connected Data

## The story

A new society president asks: "Where did our reserve fund go?" The agent queries the graph and reports risk signals worth review:

- Flats with long-overdue or waived dues that connect to the old president through relatives or friends
- The same vendor getting repeated complaints that keep reopening
- Transfers recorded only in a secret ledger, passed on from vendor to shell company to outside trust
- Shared addresses between people and companies
- Decisions made with no meeting or no quorum

Decoys (a proper medical waiver, a paying relative, a genuine defaulter, an honest vendor) are not flagged.

## How FalkorDB is used

FalkorDB is the core of the product. Every risk signal is a Cypher query, not a Python loop. The agent cannot answer without running them.

- `shortestPath` from the reserve fund to the trust through transfers
- Multi-hop traversal (`RELATIVE_OF|FRIEND_OF*1..3`) from the old president to flat owners
- `REOPENS` chains over repeated complaints
- Pattern matching for transfers recorded only in the secret ledger with no approving decision
- Shared-address matching and decisions with no meeting or quorum

The agent runs the queries, logs each Cypher query and its rows, and an LLM writes the summary from that evidence. The Agent page in the UI shows every query under "How it got there".

## Run locally

Requirements: Docker, Python 3.10+, a free Groq API key.

1. Start FalkorDB (Browser at http://localhost:3000):
```
   docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest
```
2. Create and activate a virtual environment, then install dependencies:
```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
```
3. Set your Groq key (PowerShell). The key is never stored in the repo:
```
   $env:GROQ_API_KEY="your-key"
```
4. Load the graph (expect 1235 nodes and 1349 edges):
```
   python loader.py
```
   The container uses `--rm`, so re-run the loader after every restart.
5. Start the app:
```
   streamlit run app.py
```
   Use the sidebar to open the **Agent** page. Or run the agent in the terminal with `python agent.py`.

## Graph data model

Graph name: `ledgerlens`

Nodes: Person, Flat, Role, ReserveFund, Vendor, Company, Trust, Address, Meeting, Ledger, Decision, Bill, Transfer, Complaint.

Relationships:

- `(Person)-[:OWNS]->(Flat)`, `(Person)-[:HOLDS_ROLE]->(Role)`
- `(Person)-[:RELATIVE_OF|FRIEND_OF]->(Person)`
- `(Person)-[:CEO_OF|DIRECTOR_OF]->(Company|Vendor|Trust)`
- `(Person|entity)-[:LIVES_AT|REGISTERED_AT]->(Address)`
- `(Flat)-[:HAS_BILL]->(Bill)-[:WAIVED_BY]->(Decision)`
- `(Decision)-[:APPROVED_BY]->(Person)`, `(Decision)-[:MADE_AT]->(Meeting)`, `(Decision)-[:ABOUT]->(Flat|Vendor)`
- `(entity)-[:SENT]->(Transfer)-[:RECEIVED_BY]->(entity)`
- `(Transfer)-[:RECORDED_IN]->(Ledger)`, `(Transfer)-[:APPROVED_BY]->(Decision)`
- `(Ledger)-[:KEPT_BY]->(Person)`
- `(Flat)-[:FILED]->(Complaint)-[:HANDLED_BY]->(Vendor)`
- `(Complaint)-[:REOPENS]->(Complaint)`

Currency columns are named `*_krw` from the original setting; amounts are shown as plain units.

## Where the Cypher lives

- `agent.py`: `TOOLS_CYPHER`, the 7 risk-signal queries the agent runs
- `investigate.py`: queries behind the Streamlit tabs
- `loader.py`: builds the graph from the CSVs in `data/ledger_csv/`

## Project files

- `data/ledger_csv/`: 16 synthetic CSVs
- `loader.py`: wipes and rebuilds the graph
- `app.py`: Streamlit workbench (5 tabs)
- `pages/Agent.py`: agent chat page showing the Cypher trail
- `agent.py`: agent (Cypher tools plus Groq LLM summary)

## AI usage

See [AI_USAGE.md](AI_USAGE.md).
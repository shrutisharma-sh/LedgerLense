import json
from groq import Groq
from falkordb import FalkorDB

g = FalkorDB(host="localhost", port=6379).select_graph("ledgerlens")
client = Groq()
MODEL = "llama-3.3-70b-versatile"


TOOLS_CYPHER = {
    "hidden_beneficiaries": """
        MATCH (k:Person {name:'Kailash Somani'})-[:RELATIVE_OF|FRIEND_OF*1..3]-(p:Person)
              -[:OWNS]->(f:Flat)-[:HAS_BILL]->(b:Bill)
        WHERE b.status <> 'paid'
        RETURN p.name AS resident, f.flat_id AS flat, count(DISTINCT b) AS unpaid_or_waived_bills
        ORDER BY unpaid_or_waived_bills DESC""",
    "levy_burden": """
        MATCH (f:Flat)-[:HAS_BILL]->(b:Bill)
        WHERE b.levy_krw > 0 AND b.status = 'paid'
        RETURN count(DISTINCT f) AS paying_flats, sum(toInteger(b.levy_krw)) AS levy_collected""",
    "repeat_repairs": """
        MATCH (c:Complaint)-[:HANDLED_BY]->(v:Vendor)
        OPTIONAL MATCH (c)-[r:REOPENS]->(:Complaint)
        WITH v.name AS vendor, c.issue AS issue, c.block AS block,
             count(DISTINCT c) AS complaints, count(r) AS reopens
        WHERE complaints >= 3
        RETURN vendor, issue, block, complaints, reopens ORDER BY complaints DESC""",
    "secret_transfers": """
        MATCH (a)-[:SENT]->(t:Transfer)-[:RECEIVED_BY]->(b),
              (t)-[:RECORDED_IN]->(:Ledger {ledger_id:'L02'})
        WHERE NOT (t)-[:APPROVED_BY]->(:Decision)
        RETURN a.name AS sender, b.name AS receiver, count(t) AS transfers,
               sum(toInteger(t.amount_krw)) AS total""",
    "reserve_to_trust_path": """
        MATCH (r:ReserveFund), (t:Trust)
        MATCH p = shortestPath((r)-[:SENT|RECEIVED_BY*]->(t))
        RETURN [n IN nodes(p) | coalesce(n.name, n.transfer_id)] AS path""",
    "shared_addresses": """
        MATCH (a)-[:LIVES_AT|REGISTERED_AT]->(ad:Address)<-[:LIVES_AT|REGISTERED_AT]-(b)
        WHERE a.name < b.name
        RETURN a.name AS first, b.name AS second, ad.text AS address""",
    "unapproved_decisions": """
        MATCH (d:Decision)
        OPTIONAL MATCH (d)-[:MADE_AT]->(m:Meeting)
        WITH d, m WHERE m IS NULL OR m.quorum_met = false
        RETURN d.decision_id AS decision, d.type AS type, d.date AS date,
               CASE WHEN m IS NULL THEN 'no meeting' ELSE 'no quorum at ' + m.meeting_id END AS reason""",
}

TOOLS = [
    {"type": "function", "function": {
        "name": n,
        "description": f"Runs a fixed Cypher query: {n.replace('_', ' ')}.",
        "parameters": {"type": "object", "properties": {}}}}
    for n in TOOLS_CYPHER
]

SYSTEM = (
    "You are LedgerLens, an assistant for Shruti Rao, new president of a housing society. "
    "Investigate using the tools (call several). Report 'risk signals worth review', never accuse "
    "anyone of fraud. Only flag what the data shows; do not flag people who merely have links. "
    "Data is synthetic. Keep the answer short: signal, evidence, suggested next step."
)


def run_agent(question):
    log = []  
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": question}]
    for _ in range(8):
        r = client.chat.completions.create(model=MODEL, messages=msgs,
                                           tools=TOOLS, tool_choice="auto",
                                           max_tokens=1500)
        m = r.choices[0].message
        if not m.tool_calls:
            return m.content, log
        msgs.append({"role": "assistant", "content": m.content or "",
                     "tool_calls": [{"id": t.id, "type": "function",
                                     "function": {"name": t.function.name,
                                                  "arguments": t.function.arguments or "{}"}}
                                    for t in m.tool_calls]})
        for t in m.tool_calls:
            cy = TOOLS_CYPHER.get(t.function.name)
            if not cy:
                msgs.append({"role": "tool", "tool_call_id": t.id, "content": "unknown tool"})
                continue
            res = g.query(cy)
            cols = [h[1] for h in res.header]
            rows = [dict(zip(cols, row)) for row in res.result_set]
            log.append({"tool": t.function.name, "cypher": cy, "rows": rows})
            msgs.append({"role": "tool", "tool_call_id": t.id,
                         "content": json.dumps(rows, default=str)})
    return "Stopped after too many steps.", log


if __name__ == "__main__":
    ans, log = run_agent("Where did our reserve fund go?")
    for l in log:
        print("TOOL:", l["tool"], l["rows"][:3])
    print("\n", ans)
import csv
from falkordb import FalkorDB

DATA = "data/ledger_csv/"
db = FalkorDB(host="localhost", port=6379)


def read(name):
    with open(DATA + name + ".csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


try:
    db.select_graph("ledgerlens").delete()
except Exception:
    pass
g = db.select_graph("ledgerlens")

g.query("CREATE INDEX FOR (p:Person) ON (p.person_id)")
g.query("CREATE INDEX FOR (f:Flat) ON (f.flat_id)")
g.query("CREATE INDEX FOR (r:Role) ON (r.role_id)")
for label in ["ReserveFund", "Vendor", "Company", "Trust"]:
    g.query(f"CREATE INDEX FOR (e:{label}) ON (e.entity_id)")
g.query("CREATE INDEX FOR (a:Address) ON (a.address_id)")
g.query("CREATE INDEX FOR (m:Meeting) ON (m.meeting_id)")
g.query("CREATE INDEX FOR (d:Decision) ON (d.decision_id)")
g.query("CREATE INDEX FOR (l:Ledger) ON (l.ledger_id)")

# nodes
g.query("""UNWIND $rows AS r
CREATE (:Person {person_id: r.person_id, name: r.name, phone: r.phone})""",
        {"rows": read("persons")})

flats = read("flats")
for r in flats:
    r["number"] = int(r["number"])
g.query("""UNWIND $rows AS r
CREATE (:Flat {flat_id: r.flat_id, block: r.block, number: r.number})""",
        {"rows": flats})

g.query("""UNWIND $rows AS r
CREATE (:Role {role_id: r.role_id, title: r.title})""",
        {"rows": read("roles")})

entities = read("entities")
for label in {r["label"] for r in entities}:
    rows = [{"entity_id": r["entity_id"], "name": r["name"],
             "opening_balance_krw": int(r["opening_balance_krw"]) if r["opening_balance_krw"] else None}
            for r in entities if r["label"] == label]
    g.query(f"""UNWIND $rows AS r
CREATE (:{label} {{entity_id: r.entity_id, name: r.name,
                   opening_balance_krw: r.opening_balance_krw}})""", {"rows": rows})

g.query("""UNWIND $rows AS r
CREATE (:Address {address_id: r.address_id, text: r.text})""",
        {"rows": read("addresses")})

meetings = read("meetings")
for r in meetings:
    r["attendees"] = int(r["attendees"])
    r["quorum_met"] = (r["quorum_met"] == "TRUE")
g.query("""UNWIND $rows AS r
CREATE (:Meeting {meeting_id: r.meeting_id, date: r.date,
                  attendees: r.attendees, quorum_met: r.quorum_met})""",
        {"rows": meetings})

ledgers = read("ledgers")
g.query("""UNWIND $rows AS r
CREATE (:Ledger {ledger_id: r.ledger_id, name: r.name})""", {"rows": ledgers})

decs = read("decisions")
g.query("""UNWIND $rows AS r
CREATE (:Decision {decision_id: r.decision_id, type: r.type, date: r.date})""",
        {"rows": decs})

# relationships
g.query("""UNWIND $rows AS r
MATCH (p:Person {person_id: r.person_id}), (f:Flat {flat_id: r.flat_id})
CREATE (p)-[:OWNS]->(f)""", {"rows": read("owns")})

g.query("""UNWIND $rows AS r
MATCH (p:Person {person_id: r.person_id}), (ro:Role {role_id: r.role_id})
CREATE (p)-[:HOLDS_ROLE {from_date: r.from_date, to_date: r.to_date}]->(ro)""",
        {"rows": read("holds_role")})

links = read("person_links")
for t in {r["rel_type"] for r in links}:
    rows = [r for r in links if r["rel_type"] == t]
    g.query(f"""UNWIND $rows AS r
MATCH (a:Person {{person_id: r.person_a}}), (b:Person {{person_id: r.person_b}})
CREATE (a)-[:{t} {{detail: r.detail}}]->(b)""", {"rows": rows})

pel = read("person_entity_links")
for t in {r["rel_type"] for r in pel}:
    rows = [r for r in pel if r["rel_type"] == t]
    g.query(f"""UNWIND $rows AS r
MATCH (p:Person {{person_id: r.person_id}}), (e {{entity_id: r.entity_id}})
CREATE (p)-[:{t}]->(e)""", {"rows": rows})

al = read("address_links")
for t in {r["rel_type"] for r in al}:
    p_rows = [r for r in al if r["rel_type"] == t and r["owner_label"] == "Person"]
    e_rows = [r for r in al if r["rel_type"] == t and r["owner_label"] != "Person"]
    if p_rows:
        g.query(f"""UNWIND $rows AS r
MATCH (o:Person {{person_id: r.owner_id}}), (a:Address {{address_id: r.address_id}})
CREATE (o)-[:{t}]->(a)""", {"rows": p_rows})
    if e_rows:
        g.query(f"""UNWIND $rows AS r
MATCH (o {{entity_id: r.owner_id}}), (a:Address {{address_id: r.address_id}})
CREATE (o)-[:{t}]->(a)""", {"rows": e_rows})

g.query("""UNWIND $rows AS r
MATCH (l:Ledger {ledger_id: r.ledger_id}), (p:Person {person_id: r.kept_by})
CREATE (l)-[:KEPT_BY]->(p)""", {"rows": ledgers})

g.query("""UNWIND $rows AS r
MATCH (d:Decision {decision_id: r.decision_id}), (p:Person {person_id: r.approved_by})
CREATE (d)-[:APPROVED_BY]->(p)""", {"rows": decs})

# D10 has no meeting, so it gets no MADE_AT edge
g.query("""UNWIND $rows AS r
MATCH (d:Decision {decision_id: r.decision_id}), (m:Meeting {meeting_id: r.meeting_id})
CREATE (d)-[:MADE_AT]->(m)""", {"rows": [r for r in decs if r["meeting_id"]]})

g.query("""UNWIND $rows AS r
MATCH (d:Decision {decision_id: r.decision_id}), (f:Flat {flat_id: r.subject_id})
CREATE (d)-[:ABOUT]->(f)""", {"rows": [r for r in decs if r["subject_label"] == "Flat"]})

g.query("""UNWIND $rows AS r
MATCH (d:Decision {decision_id: r.decision_id}), (v {entity_id: r.subject_id})
CREATE (d)-[:ABOUT]->(v)""", {"rows": [r for r in decs if r["subject_label"] == "Vendor"]})

g.query("CREATE INDEX FOR (b:Bill) ON (b.bill_id)")
g.query("CREATE INDEX FOR (t:Transfer) ON (t.transfer_id)")
g.query("CREATE INDEX FOR (c:Complaint) ON (c.complaint_id)")

# bills
bills = read("bills")
for r in bills:
    for k in ("base_krw", "levy_krw", "paid_krw"):
        r[k] = int(r[k])
g.query("""UNWIND $rows AS r
CREATE (:Bill {bill_id: r.bill_id, month: r.month, base_krw: r.base_krw,
               levy_krw: r.levy_krw, status: r.status, paid_krw: r.paid_krw})""",
        {"rows": bills})
g.query("""UNWIND $rows AS r
MATCH (f:Flat {flat_id: r.flat_id}), (b:Bill {bill_id: r.bill_id})
CREATE (f)-[:HAS_BILL]->(b)""", {"rows": bills})
g.query("""UNWIND $rows AS r
MATCH (b:Bill {bill_id: r.bill_id}), (d:Decision {decision_id: r.decision_id})
CREATE (b)-[:WAIVED_BY]->(d)""", {"rows": [r for r in bills if r["decision_id"]]})

# transfers
transfers = read("transfers")
for r in transfers:
    r["amount_krw"] = int(r["amount_krw"])
g.query("""UNWIND $rows AS r
CREATE (:Transfer {transfer_id: r.transfer_id, date: r.date,
                   amount_krw: r.amount_krw, purpose: r.purpose})""",
        {"rows": transfers})
g.query("""UNWIND $rows AS r
MATCH (a {entity_id: r.from_id}), (t:Transfer {transfer_id: r.transfer_id})
CREATE (a)-[:SENT]->(t)""", {"rows": transfers})
g.query("""UNWIND $rows AS r
MATCH (t:Transfer {transfer_id: r.transfer_id}), (b {entity_id: r.to_id})
CREATE (t)-[:RECEIVED_BY]->(b)""", {"rows": transfers})
g.query("""UNWIND $rows AS r
MATCH (t:Transfer {transfer_id: r.transfer_id}), (l:Ledger {ledger_id: r.ledger_id})
CREATE (t)-[:RECORDED_IN]->(l)""", {"rows": [r for r in transfers if r["ledger_id"]]})
g.query("""UNWIND $rows AS r
MATCH (t:Transfer {transfer_id: r.transfer_id}), (d:Decision {decision_id: r.decision_id})
CREATE (t)-[:APPROVED_BY]->(d)""", {"rows": [r for r in transfers if r["decision_id"]]})

# complaints
complaints = read("complaints")
g.query("""UNWIND $rows AS r
CREATE (:Complaint {complaint_id: r.complaint_id, issue: r.issue, block: r.block,
                    opened: r.opened, closed: r.closed})""", {"rows": complaints})
g.query("""UNWIND $rows AS r
MATCH (f:Flat {flat_id: r.flat_id}), (c:Complaint {complaint_id: r.complaint_id})
CREATE (f)-[:FILED]->(c)""", {"rows": complaints})
g.query("""UNWIND $rows AS r
MATCH (c:Complaint {complaint_id: r.complaint_id}), (v {entity_id: r.vendor_id})
CREATE (c)-[:HANDLED_BY]->(v)""", {"rows": complaints})
g.query("""UNWIND $rows AS r
MATCH (c:Complaint {complaint_id: r.complaint_id}), (p:Complaint {complaint_id: r.reopened_of})
CREATE (c)-[:REOPENS]->(p)""", {"rows": [r for r in complaints if r["reopened_of"]]})

print("nodes:", g.query("MATCH (n) RETURN count(n)").result_set)
print("edges:", g.query("MATCH ()-[e]->() RETURN count(e)").result_set)
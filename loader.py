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


#nodes 
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


#relationships
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

print("nodes:", g.query("MATCH (n) RETURN count(n)").result_set)
print("edges:", g.query("MATCH ()-[e]->() RETURN count(e)").result_set)
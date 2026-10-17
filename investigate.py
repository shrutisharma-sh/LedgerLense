
from falkordb import FalkorDB

db = FalkorDB(host="localhost", port=6379)
g = db.select_graph("ledgerlens")


def run_query(query):
    return g.query(query).result_set


def hidden_beneficiaries():
    return run_query("""
    MATCH (p:Person)-[:OWNS]->(f:Flat)-[:HAS_BILL]->(b:Bill)
    WHERE b.status = 'UNPAID'
    WITH p, f, count(b) AS unpaid_months
    WHERE unpaid_months >= 12
    MATCH (p)-[:RELATIVE_OF|FRIEND_OF]-(president:Person)
    WHERE president.name = 'Kailash Somani'
    RETURN p.name, f.flat_id, unpaid_months
    ORDER BY unpaid_months DESC
    """)


def waiver_check():
    return run_query("""
    MATCH (f:Flat)-[:HAS_BILL]->(b:Bill)-[:WAIVED_BY]->(d:Decision)
    MATCH (p:Person)-[:OWNS]->(f)
    WHERE d.decision_id = 'D10'
    OPTIONAL MATCH (d)-[:APPROVED_BY]->(approver:Person)
    OPTIONAL MATCH (d)-[:MADE_AT]->(m:Meeting)
    RETURN f.flat_id, p.name, count(b) AS waived_bills,
           collect(DISTINCT approver.name) AS approvers,
           collect(DISTINCT m.meeting_id) AS meetings
    """)


def residents_levy():
    return run_query("""
    MATCH (f:Flat)-[:HAS_BILL]->(b:Bill)
    WHERE b.levy_krw > 0 AND b.month >= '2025-04'
    RETURN b.month, count(DISTINCT f) AS flats,
           sum(b.levy_krw) AS total_levy
    ORDER BY b.month
    """)


def recurring_repairs():
    return run_query("""
    MATCH (c:Complaint)-[:HANDLED_BY]->(v:Vendor)
    MATCH (c)-[:REOPENS]->(previous:Complaint)
    WITH v, c.issue AS issue, c.block AS block,
         count(DISTINCT c) AS reopened_complaints
    WHERE reopened_complaints >= 3
    RETURN v.name, issue, block, reopened_complaints
    ORDER BY reopened_complaints DESC
    """)


def secret_transfers():
    return run_query("""
    MATCH (t:Transfer)-[:RECORDED_IN]->(l:Ledger {ledger_id: 'L02'})
    RETURN count(t) AS transfers, sum(t.amount_krw) AS total_krw
    """)


def money_path():
    return run_query("""
    MATCH (fund:ReserveFund)-[:SENT]->(t:Transfer)-[:RECEIVED_BY]->(vendor:Vendor)
    RETURN DISTINCT fund.name, vendor.name,
           t.transfer_id, t.amount_krw, t.date, t.purpose
    ORDER BY t.date
    LIMIT 10
    """)


def show(title, query_fn):
    print(f"\n{'=' * 12} {title} {'=' * 12}")
    try:
        rows = query_fn()
        if not rows:
            print("No matching records found.")
        for row in rows:
            print(" | ".join(str(value) for value in row))
    except Exception as error:
        print(f"Query error: {error}")


if __name__ == "__main__":
    show("POTENTIAL CONNECTED DEFAULTERS", hidden_beneficiaries)
    show("WAIVER REVIEW", waiver_check)
    show("SPECIAL LEVY BY MONTH", residents_levy)
    show("REOPENED COMPLAINTS", recurring_repairs)
    show("TRANSFERS IN LEDGER L02", secret_transfers)
    show("RECENT RESERVE FUND TRANSFERS", money_path)

    print("\nSynthetic data. Risk signals, not accusations.")

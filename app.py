import streamlit as st
from falkordb import FalkorDB

st.set_page_config(page_title="LeadgerLense", page_icon="🔎", layout="wide")

@st.cache_resource
def get_graph():
    return FalkorDB(host="localhost", port=6379).select_graph("ledgerlens")

g = get_graph()


def query(cypher):
    return g.query(cypher).result_set


def table(rows, headers):
    if rows:
        st.dataframe(
            [dict(zip(headers, row)) for row in rows],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No matching records found.")


st.title("🔎 Civic Guard")
st.caption("AI-powered civic investigation | Synthetic data. Risk signals, not accusations.")

try:
    nodes = query("MATCH (n) RETURN count(n)")[0][0]
    edges = query("MATCH ()-[r]->() RETURN count(r)")[0][0]
    secret = query("""
        MATCH (t:Transfer)-[:RECORDED_IN]->(:Ledger {ledger_id:'L02'})
        RETURN count(t), sum(t.amount_krw)
    """)[0]

    a, b, c, d = st.columns(4)
    a.metric("Graph nodes", f"{nodes:,}")
    b.metric("Relationships", f"{edges:,}")
    c.metric("L02 transfers", secret[0] or 0)
    d.metric("L02 transfer value", f"₩{secret[1] or 0:,.0f}")

    st.divider()
    st.subheader("Investigation agent")

    investigations = [
        "Find connected residents with long-term unpaid bills",
        "Trace transfers in the secret ledger",
        "Trace the complete money flow",
        "Review shared addresses and company links",
        "Find recurring reopened complaints",
        "Review decisions and meeting quorum",
        "Compare all bill waivers",
    ]

    question = st.selectbox("Choose an investigation", investigations)

    if st.button("Run investigation", type="primary"):
        if question == investigations[0]:
            st.write("**Finding:** Residents with at least 12 unpaid bills and a recorded family/friend link to the president.")
            rows = query("""
                MATCH (p:Person)-[:OWNS]->(f:Flat)-[:HAS_BILL]->(b:Bill)
                WHERE b.status = 'UNPAID'
                WITH p, f, count(b) AS months
                WHERE months >= 12
                MATCH (p)-[:RELATIVE_OF|FRIEND_OF]-(president:Person)
                WHERE president.name = 'Kailash Somani'
                RETURN DISTINCT p.name, f.flat_id, months
                ORDER BY months DESC
            """)
            table(rows, ["Resident", "Flat", "Unpaid months"])

        elif question == investigations[1]:
            st.write("**Finding:** Transfers recorded in ledger L02.")
            rows = query("""
                MATCH (t:Transfer)-[:RECORDED_IN]->(l:Ledger {ledger_id:'L02'})
                OPTIONAL MATCH (fund:ReserveFund)-[:SENT]->(t)
                OPTIONAL MATCH (t)-[:RECEIVED_BY]->(recipient)
                RETURN DISTINCT t.transfer_id, t.date, fund.name,
                       recipient.name, t.amount_krw, t.purpose
                ORDER BY t.date
            """)
            table(rows, ["Transfer", "Date", "Sender", "Recipient", "Amount (KRW)", "Purpose"])

        elif question == investigations[2]:
            st.write("**Money flow:** Reserve fund → SH-Group → Surya Consulting → Residents' Welfare Trust.")
            rows = query("""
                MATCH (fund:ReserveFund)-[:SENT]->(t1:Transfer)-[:RECEIVED_BY]->(v:Vendor)
                MATCH (v)-[:SENT]->(t2:Transfer)-[:RECEIVED_BY]->(c:Company)
                MATCH (c)-[:SENT]->(t3:Transfer)-[:RECEIVED_BY]->(trust:Trust)
                RETURN DISTINCT fund.name, v.name,
                       t1.transfer_id, t1.amount_krw, t1.date,
                       c.name, t2.transfer_id, t2.amount_krw,
                       trust.name, t3.transfer_id, t3.amount_krw
                ORDER BY t1.date
            """)
            table(rows, [
                "Source", "First recipient", "Transfer 1", "Amount 1 (KRW)",
                "Date 1", "Company", "Transfer 2", "Amount 2 (KRW)",
                "Final recipient", "Transfer 3", "Amount 3 (KRW)"
            ])
            st.caption("Transfer amounts are shown individually. They should not be added across stages as if they were separate losses.")

        elif question == investigations[3]:
            rows = query("""
                MATCH (p:Person)-[:LIVES_AT|REGISTERED_AT]->(a:Address)
                WITH a, collect(DISTINCT p.name) AS people
                WHERE size(people) > 1
                RETURN a.address_id, a.text, people
                ORDER BY a.address_id
            """)
            st.write("**Shared addresses**")
            table(rows, ["Address ID", "Address", "People"])

            rows = query("""
                MATCH (p:Person)-[r:DIRECTOR_OF|CEO_OF]->(e)
                RETURN p.name, type(r), e.name
                ORDER BY e.name
            """)
            st.write("**Company and trust roles**")
            table(rows, ["Person", "Relationship", "Entity"])

            rows = query("""
                MATCH (p1:Person)-[r:RELATIVE_OF|FRIEND_OF]-(p2:Person)
                RETURN DISTINCT p1.name, type(r), p2.name
                ORDER BY p1.name
            """)
            st.write("**Recorded personal links**")
            table(rows, ["Person", "Relationship", "Connected person"])

        elif question == investigations[4]:
            rows = query("""
                MATCH (c:Complaint)-[:REOPENS]->(previous:Complaint)
                MATCH (c)-[:HANDLED_BY]->(v:Vendor)
                RETURN v.name, c.issue, c.block,
                       count(DISTINCT c) AS reopened_cases
                ORDER BY reopened_cases DESC
            """)
            st.write("**Complaints linked to reopened cases**")
            table(rows, ["Vendor", "Issue", "Block", "Reopened cases"])

        elif question == investigations[5]:
            rows = query("""
                MATCH (d:Decision)
                OPTIONAL MATCH (d)-[:APPROVED_BY]->(p:Person)
                OPTIONAL MATCH (d)-[:MADE_AT]->(m:Meeting)
                RETURN d.decision_id, d.type, d.date,
                       collect(DISTINCT p.name),
                       collect(DISTINCT m.meeting_id),
                       collect(DISTINCT m.quorum_met)
                ORDER BY d.date
            """)
            table(rows, [
                "Decision", "Type", "Date", "Approvers",
                "Meetings", "Quorum status"
            ])
            st.caption("Decisions without a linked meeting are retained for review rather than silently excluded.")

        else:
            rows = query("""
                MATCH (p:Person)-[:OWNS]->(f:Flat)-[:HAS_BILL]->(b:Bill)
                      -[:WAIVED_BY]->(d:Decision)
                OPTIONAL MATCH (d)-[:APPROVED_BY]->(approver:Person)
                OPTIONAL MATCH (d)-[:MADE_AT]->(m:Meeting)
                RETURN p.name, f.flat_id, d.decision_id,
                       count(DISTINCT b) AS waived_bills,
                       collect(DISTINCT approver.name),
                       collect(DISTINCT m.meeting_id),
                       collect(DISTINCT m.quorum_met)
                ORDER BY waived_bills DESC
            """)
            table(rows, [
                "Resident", "Flat", "Decision", "Waived bills",
                "Approvers", "Meetings", "Quorum status"
            ])
            st.caption("Compare waiver approvals and meeting records. A waiver alone does not establish wrongdoing.")

    st.divider()
    st.subheader("Investigation workbench")

    tabs = st.tabs([
        "Connected residents",
        "Complaint patterns",
        "Ledger trail",
        "Decision review",
        "Evidence explorer",
    ])

    with tabs[0]:
        rows = query("""
            MATCH (p:Person)-[:OWNS]->(f:Flat)-[:HAS_BILL]->(b:Bill)
            WHERE b.status = 'UNPAID'
            WITH p, f, count(b) AS months
            WHERE months >= 12
            MATCH (p)-[:RELATIVE_OF|FRIEND_OF]-(president:Person)
            WHERE president.name = 'Kailash Somani'
            RETURN DISTINCT p.name, f.flat_id, months
            ORDER BY months DESC
        """)
        table(rows, ["Resident", "Flat", "Unpaid months"])

        rows = query("""
            MATCH (p:Person)-[:OWNS]->(f:Flat)-[:HAS_BILL]->(b:Bill)
            WHERE b.status = 'UNPAID'
            WITH p, f, count(b) AS months
            WHERE months >= 12
            MATCH (p)-[:RELATIVE_OF|FRIEND_OF]-(president:Person)
            WHERE president.name = 'Kailash Somani'
            MATCH (p)-[r:RELATIVE_OF|FRIEND_OF]-(president)
            RETURN DISTINCT p.name, type(r), president.name
        """)
        st.write("**Relationship evidence**")
        table(rows, ["Resident", "Relationship", "President"])

    with tabs[1]:
        rows = query("""
            MATCH (c:Complaint)-[:REOPENS]->(previous:Complaint)
            MATCH (c)-[:HANDLED_BY]->(v:Vendor)
            RETURN v.name, c.issue, c.block,
                   count(DISTINCT c) AS reopened_cases
            ORDER BY reopened_cases DESC
        """)
        table(rows, ["Vendor", "Issue", "Block", "Reopened cases"])

    with tabs[2]:
        rows = query("""
            MATCH (t:Transfer)-[:RECORDED_IN]->(l:Ledger {ledger_id:'L02'})
            OPTIONAL MATCH (:ReserveFund)-[:SENT]->(t)
            OPTIONAL MATCH (t)-[:RECEIVED_BY]->(recipient)
            RETURN DISTINCT t.transfer_id, t.date, t.amount_krw,
                   t.purpose, l.ledger_id, recipient.name
            ORDER BY t.date
        """)
        table(rows, [
            "Transfer", "Date", "Amount (KRW)",
            "Purpose", "Ledger", "Recipient"
        ])

        rows = query("""
            MATCH (fund:ReserveFund)-[:SENT]->(t1:Transfer)-[:RECEIVED_BY]->(v:Vendor)
            MATCH (v)-[:SENT]->(t2:Transfer)-[:RECEIVED_BY]->(c:Company)
            MATCH (c)-[:SENT]->(t3:Transfer)-[:RECEIVED_BY]->(trust:Trust)
            RETURN DISTINCT fund.name, v.name, c.name, trust.name,
                   t1.transfer_id, t2.transfer_id, t3.transfer_id
            LIMIT 20
        """)
        st.write("**Connected transfer path**")
        table(rows, [
            "Source", "Vendor", "Company", "Trust",
            "Transfer 1", "Transfer 2", "Transfer 3"
        ])

    with tabs[3]:
        rows = query("""
            MATCH (d:Decision)
            OPTIONAL MATCH (d)-[:APPROVED_BY]->(p:Person)
            OPTIONAL MATCH (d)-[:MADE_AT]->(m:Meeting)
            RETURN d.decision_id, d.type, d.date,
                   collect(DISTINCT p.name),
                   collect(DISTINCT m.meeting_id),
                   collect(DISTINCT m.quorum_met)
            ORDER BY d.date
        """)
        table(rows, [
            "Decision", "Type", "Date", "Approvers",
            "Meetings", "Quorum status"
        ])

        rows = query("""
            MATCH (p:Person)-[:OWNS]->(f:Flat)-[:HAS_BILL]->(b:Bill)
                  -[:WAIVED_BY]->(d:Decision)
            RETURN p.name, f.flat_id, d.decision_id, count(b)
            ORDER BY count(b) DESC
        """)
        st.write("**Waived bills by decision**")
        table(rows, ["Resident", "Flat", "Decision", "Waived bills"])

    with tabs[4]:
        rows = query("""
            MATCH (p:Person)-[:LIVES_AT|REGISTERED_AT]->(a:Address)
            WITH a, collect(DISTINCT p.name) AS people
            WHERE size(people) > 1
            RETURN a.address_id, a.text, people
            ORDER BY a.address_id
        """)
        st.write("**Shared-address evidence**")
        table(rows, ["Address ID", "Address", "Connected people"])

        rows = query("""
            MATCH (p:Person)-[r:DIRECTOR_OF|CEO_OF]->(e)
            RETURN p.name, type(r), e.name
            ORDER BY e.name
        """)
        st.write("**Company-role evidence**")
        table(rows, ["Person", "Relationship", "Entity"])

    st.divider()
    st.caption(
        "Synthetic data. Risk signals, not accusations. "
        "Findings require human verification."
    )

except Exception as e:
    st.error(
        "Could not load Civic Guard. Check that FalkorDB is running "
        "and the ledgerlens graph is loaded."
    )
    st.code(str(e))

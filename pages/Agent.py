import streamlit as st
from agent import run_agent

st.title("Ask the agent")
st.caption("Synthetic data. Risk signals, not accusations.")

q = st.text_input("Question", "Where did our reserve fund go?")
if st.button("Ask", type="primary"):
    with st.spinner("Querying the graph..."):
        answer, log = run_agent(q)
    st.markdown(answer)
    st.subheader("How it got there")
    for l in log:
        with st.expander(l["tool"]):
            st.code(l["cypher"], language="cypher")
            st.dataframe(l["rows"])
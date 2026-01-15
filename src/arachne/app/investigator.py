from __future__ import annotations

import os
from dataclasses import dataclass

import streamlit as st
from neo4j import GraphDatabase
import pandas as pd



def show_table(rows: list[dict], *, sort_by: str | None = None, descending: bool = True):
    # For displaying query results nicely in Streamlit
    if not rows:
        st.info("No rows.")
        return

    df = pd.DataFrame(rows)

    # Optional sorting
    if sort_by and sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=not descending)

    # Nicer column labels
    rename = {
        "tx_total": "tx_total",
        "tx_fraud": "tx_fraud",
        "fraud_rate": "fraud_rate",
        "people_count": "people",
        "linked_person": "linked_person",
        "shared_device": "shared_device",
        "shared_card": "shared_card",
        "shared_address": "shared_address",
        "shared_ip": "shared_ip",
        "weight": "weight",
        "artifact": "artifact",
        "tx_count": "tx_count",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    styler = df.style

    # Format a few columns cleanly
    if "fraud_rate" in df.columns:
        styler = styler.format({"fraud_rate": "{:.4f}"})
    if "weight" in df.columns:
        styler = styler.format({"weight": "{:.0f}"})

    # Highlight columns that matter with color gradients
    # Fraud rate: higher = hotter
    if "fraud_rate" in df.columns:
        styler = styler.background_gradient(subset=["fraud_rate"], cmap="Reds")

    # Fraud tx: higher = hotter
    if "tx_fraud" in df.columns:
        styler = styler.background_gradient(subset=["tx_fraud"], cmap="Oranges")

    # Weight: higher = hotter
    if "weight" in df.columns:
        styler = styler.background_gradient(subset=["weight"], cmap="Purples")

    # Shared evidence counts: higher = hotter
    shared_cols = [c for c in ["shared_device", "shared_card", "shared_address", "shared_ip"] if c in df.columns]
    if shared_cols:
        styler = styler.background_gradient(subset=shared_cols, cmap="Blues")

    # Make it easier to read
    styler = styler.set_properties(**{"font-size": "0.92rem"}).set_table_styles(
        [{"selector": "th", "props": [("text-align", "left")]}]
    )

    st.dataframe(styler, use_container_width=True, hide_index=True)


@dataclass(frozen=True)
class Neo4jCfg:
    uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user: str = os.getenv("NEO4J_USER", "neo4j")
    password: str = os.getenv("NEO4J_PASSWORD", "password123")
    database: str = os.getenv("NEO4J_DATABASE", "neo4j")


def run_query(cfg: Neo4jCfg, cypher: str, params: dict | None = None):
    driver = GraphDatabase.driver(cfg.uri, auth=(cfg.user, cfg.password))
    try:
        with driver.session(database=cfg.database) as session:
            res = session.run(cypher, params or {})
            return [r.data() for r in res]
    finally:
        driver.close()


st.set_page_config(page_title="Arachne Investigator Console", layout="wide")
st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

      h1 { letter-spacing: 0.2px; }
      h2, h3 { margin-top: 0.6rem; }

      .kpi {
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 14px;
        padding: 14px 14px 10px 14px;
        background: rgba(255,255,255,0.03);
      }
      .kpi-label { font-size: 0.85rem; opacity: 0.75; margin-bottom: 6px; }
      .kpi-value { font-size: 1.55rem; font-weight: 650; line-height: 1.2; }
      .kpi-sub { font-size: 0.85rem; opacity: 0.70; margin-top: 6px; }

      section[data-testid="stSidebar"] .block-container { padding-top: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Arachne Investigator Console")

cfg = Neo4jCfg()

with st.sidebar:
    st.header("Connection")
    st.caption("Uses env vars if set: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE")
    if st.button("Ping Neo4j"):
        try:
            out = run_query(cfg, "RETURN 1 AS ok")
            st.success(f"Connected ({out[0]['ok']})")
        except Exception as e:
            st.error(f"Connection failed: {e}")

    st.divider()
    st.header("Search")
    person_id = st.text_input("Person ID", value=st.session_state.get("person_id", "P001749"))
community_id = st.number_input(
    "Community ID (community_id_strong)",
    value=int(st.session_state.get("community_id", 228)),
    step=1,
)

st.divider()
st.subheader("Community members")

q_members = """
MATCH (p:Person)
WHERE p.community_id_strong = $cid
RETURN p.person_id AS person_id
ORDER BY person_id;
"""

try:
    member_rows = run_query(cfg, q_members, {"cid": int(community_id)})
    member_ids = [r["person_id"] for r in member_rows]

    if not member_ids:
        st.caption("No members found for this community.")
    else:
        picked = st.selectbox(
            "Pick a person in this community",
            options=member_ids,
            index=member_ids.index(person_id.strip()) if person_id.strip() in member_ids else 0,
        )
        if st.button("Set as current suspect"):
            st.session_state["person_id"] = picked
            st.rerun()

        st.caption(f"{len(member_ids)} people in community {int(community_id)}")
except Exception as e:
    st.error(str(e))


if st.button("Use suspect's community"):
    # Looks up the suspect's community and update session state
    q = """
    MATCH (p:Person {person_id: $pid})
    RETURN p.community_id_strong AS cid;
    """
    try:
        res = run_query(cfg, q, {"pid": person_id.strip()})
        if res and res[0]["cid"] is not None:
            st.session_state["community_id"] = int(res[0]["cid"])
            st.session_state["person_id"] = person_id.strip()
            st.rerun()
        else:
            st.warning("No community_id_strong found for this person.")
    except Exception as e:
        st.error(str(e))


colA, colB = st.columns([1, 1], gap="large")

with colA:
    st.subheader("Top suspicious communities (multi-person)")

    q_comm = """
    MATCH (p:Person)-[:MADE]->(t:Transaction)
    WHERE p.community_id_strong IS NOT NULL
    WITH p.community_id_strong AS community,
         count(DISTINCT p) AS people_count,
         count(t) AS tx_total,
         sum(CASE WHEN t.is_fraud = 1 THEN 1 ELSE 0 END) AS tx_fraud
    WHERE people_count >= 5
    RETURN community, people_count, tx_total, tx_fraud,
           round(1.0 * tx_fraud / tx_total, 4) AS fraud_rate
    ORDER BY fraud_rate DESC, tx_fraud DESC
    LIMIT 10;
    """
    try:
        rows = run_query(cfg, q_comm)
        show_table(rows, sort_by="fraud_rate", descending=True)
    except Exception as e:
        st.error(str(e))

with colB:
    st.subheader("Community snapshot")

    q_snap = """
    MATCH (p:Person)-[:MADE]->(t:Transaction)
    WHERE p.community_id_strong = $cid
    WITH count(DISTINCT p) AS people_count,
         count(t) AS tx_total,
         sum(CASE WHEN t.is_fraud = 1 THEN 1 ELSE 0 END) AS tx_fraud
    RETURN people_count, tx_total, tx_fraud,
           round(1.0 * tx_fraud / tx_total, 4) AS fraud_rate;
    """
    try:
        snap = run_query(cfg, q_snap, {"cid": int(community_id)})
        if snap:
            s = snap[0]
            c1, c2, c3, c4 = st.columns(4, gap="medium")
            c1.markdown(f"<div class='kpi'><div class='kpi-label'>People</div><div class='kpi-value'>{s['people_count']}</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='kpi'><div class='kpi-label'>Transactions</div><div class='kpi-value'>{s['tx_total']}</div></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='kpi'><div class='kpi-label'>Fraud Tx</div><div class='kpi-value'>{s['tx_fraud']}</div></div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='kpi'><div class='kpi-label'>Fraud Rate</div><div class='kpi-value'>{s['fraud_rate']}</div><div class='kpi-sub'>community_id_strong</div></div>", unsafe_allow_html=True)

        else:
            st.info("No results for that community_id_strong.")
    except Exception as e:
        st.error(str(e))

st.divider()
st.subheader("Suspect overview")

q_sus = """
MATCH (p:Person {person_id: $pid})-[:MADE]->(t:Transaction)
WITH p,
     count(t) AS tx_total,
     sum(CASE WHEN t.is_fraud = 1 THEN 1 ELSE 0 END) AS tx_fraud
RETURN p.person_id AS person_id,
       p.community_id_strong AS community_id_strong,
       tx_total,
       tx_fraud,
       round(1.0 * tx_fraud / tx_total, 4) AS fraud_rate;
"""
try:
    sus = run_query(cfg, q_sus, {"pid": person_id.strip()})
    if sus:
        s = sus[0]
        c1, c2, c3, c4, c5 = st.columns(5, gap="medium")
        c1.markdown(f"<div class='kpi'><div class='kpi-label'>Person</div><div class='kpi-value'>{s['person_id']}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='kpi'><div class='kpi-label'>Community</div><div class='kpi-value'>{s['community_id_strong']}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='kpi'><div class='kpi-label'>Tx Total</div><div class='kpi-value'>{s['tx_total']}</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='kpi'><div class='kpi-label'>Fraud Tx</div><div class='kpi-value'>{s['tx_fraud']}</div></div>", unsafe_allow_html=True)
        c5.markdown(f"<div class='kpi'><div class='kpi-label'>Fraud Rate</div><div class='kpi-value'>{s['fraud_rate']}</div></div>", unsafe_allow_html=True)

    else:
        st.warning("Person not found (or has no transactions).")
except Exception as e:
    st.error(str(e))

st.subheader("Top linked neighbours (evidence)")

q_neigh = """
MATCH (p:Person {person_id: $pid})-[r:LINKED_TO]-(q:Person)
RETURN q.person_id AS linked_person,
       r.w AS weight,
       r.shared_device AS shared_device,
       r.shared_card AS shared_card,
       r.shared_address AS shared_address,
       r.shared_ip AS shared_ip
ORDER BY weight DESC
LIMIT 25;
"""
try:
    neigh = run_query(cfg, q_neigh, {"pid": person_id.strip()})
    show_table(neigh, sort_by="weight", descending=True)
except Exception as e:
    st.error(str(e))


st.divider()
st.subheader("Community explorer (shared infrastructure)")

tabs = st.tabs(["Cards", "Devices", "Addresses", "IPs"])

q_cards = """
MATCH (p:Person)-[:MADE]->(:Transaction)-[:PAID_WITH]->(c:Card)
WHERE p.community_id_strong = $cid
RETURN c.card_hash AS artifact,
       count(DISTINCT p) AS people_count,
       count(*) AS tx_count
ORDER BY people_count DESC, tx_count DESC
LIMIT 20;
"""

q_devices = """
MATCH (p:Person)-[:MADE]->(:Transaction)-[:USED_DEVICE]->(d:Device)
WHERE p.community_id_strong = $cid
RETURN d.device_id AS artifact,
       count(DISTINCT p) AS people_count,
       count(*) AS tx_count
ORDER BY people_count DESC, tx_count DESC
LIMIT 20;
"""

q_addresses = """
MATCH (p:Person)-[:MADE]->(:Transaction)-[:BILLED_TO]->(a:Address)
WHERE p.community_id_strong = $cid
RETURN a.address_hash AS artifact,
       count(DISTINCT p) AS people_count,
       count(*) AS tx_count
ORDER BY people_count DESC, tx_count DESC
LIMIT 20;
"""

q_ips = """
MATCH (p:Person)-[:MADE]->(:Transaction)-[:FROM_IP]->(ip:IP)
WHERE p.community_id_strong = $cid
RETURN ip.ip AS artifact,
       count(DISTINCT p) AS people_count,
       count(*) AS tx_count
ORDER BY people_count DESC, tx_count DESC
LIMIT 20;
"""

cid_param = {"cid": int(community_id)}

with tabs[0]:
    try:
        show_table(run_query(cfg, q_cards, cid_param), sort_by="people_count", descending=True)
    except Exception as e:
        st.error(str(e))

with tabs[1]:
    try:
        show_table(run_query(cfg, q_cards, cid_param), sort_by="people_count", descending=True)
    except Exception as e:
        st.error(str(e))

with tabs[2]:
    try:
        show_table(run_query(cfg, q_cards, cid_param), sort_by="people_count", descending=True)
    except Exception as e:
        st.error(str(e))

with tabs[3]:
    try:
        show_table(run_query(cfg, q_cards, cid_param), sort_by="people_count", descending=True)
    except Exception as e:
        st.error(str(e))

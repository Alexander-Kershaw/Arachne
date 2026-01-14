***
# Arachne
***
Fraud-ring detection with graph intelligence (Neo4j).

Arachne models transactions, identities, and shared infrastructure (devices, IPs, cards, addresses) as a graph, then uses graph algorithms to surface coordinated fraud rings and produce explainable risk signals.

## What Defines Arachne?
- **Graph data model** for payments + identity infrastructure
- **Ring discovery** using community detection (Leiden/Louvain)
- **Risk scoring** with explainable evidence (shared artifacts + graph structure)
- **Investigator console** (Streamlit) for exploring suspects and rings

## Planned deliverables
- Synthetic but realistic fraud simulation dataset (reproducible seed)
- Neo4j graph load pipeline (batch + incremental)
- Graph feature builder (person-to-person inferred links)
- GDS analytics pipeline (communities + centrality + similarity)
- Risk scoring outputs + explanation paths
- Streamlit dashboard for investigation workflows

## Repository structure
- `src/arachne/simulator/` synthetic data generator
- `src/arachne/etl/` bronze → silver transforms and validation
- `src/arachne/graph_load/` Neo4j load utilities + constraints setup
- `src/arachne/graph_features/` inferred person-to-person links
- `src/arachne/gds/` graph algorithms + writeback
- `src/arachne/scoring/` risk scoring + explainability
- `src/arachne/app/` Streamlit investigator console
- `cypher/` Cypher scripts (constraints, indexes, investigator queries)
- `configs/` configuration templates (copy example → local config)
- `data/` local datasets (gitignored)
- `docs/` design notes

## Tech stack
- Python (ETL, simulation, scoring, app)
- Neo4j + Graph Data Science (graph storage + algorithms)
- Streamlit (investigation console)
- Polars/Pandas (data wrangling as needed)

## Setup (local)
### 1) Create environment
```bash
conda env create -f environment.yml
conda activate arachne
```

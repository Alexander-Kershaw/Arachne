***
# Arachne 
***

Arachne is fraud-ring detection project with graph intelligence (Neo4j and Graph Data Science).

Arachne models transactions, identities, and shared infrastructure (devices, IPs, cards, addresses) as a graph, then uses graph algorithms to surface coordinated fraud communities and produce explainable risk signals.

---

## What does Arachne do?

### Graph modelling (Neo4j)
- Creates nodes for: `Person`, `Transaction`, `Merchant`, `Device`, `IP`, `Card`, `Address`
- Creates relationships such as:
  - `(Person)-[:MADE]->(Transaction)`
  - `(Transaction)-[:USED_DEVICE]->(Device)`
  - `(Transaction)-[:PAID_WITH]->(Card)`
  - etc.

### Fraud community detection (Graph Data Science)
- Builds person-to-person linkage edges `LINKED_TO` based on shared infrastructure
- Projects the person network into Neo4j Graph Data Science
- Runs Leiden community detection to identify suspicious communities

### Explainability 
Arachne supports explainable graph evidence such as:
- shared cards used by multiple people
- shared devices across clusters
- shared billing addresses / IP infrastructure
- top linked neighbours for a suspect with breakdown counts

---

## Repository structure

- `src/arachne/simulator/` synthetic fraud simulation with fraug ring incident injection
- `src/arachne/graph_load/` Neo4j loading utilities
- `cypher/` constraints/indexes and investigation queries
- `docs/` investigation playbook and design notes
- `data/` local data lake (gitignored)
- `docker/` Hosting neo4j browser
- `scripts/` schema application and neo4j setup

---

## Setup

### 1) Create the Conda environment
```bash
conda env create -f environment.yml
conda activate arachne
```


### 2) Start Neo4j (Docker)
```bash
docker compose -f docker/docker-compose.yml up -d
```

**Neo4j Browser:**

http://localhost:7474

Login: neo4j / password123


### 3) Apply schema (constraints and indexes)

```bash
python scripts/setup_neo4j.py
```

---

### 4) Generate synthetic bronze data

**Generate bronze tables**
```bash
python -m arachne.simulator.generate_bronze
```

**Add shared infrastructure (devices/IP/cards/addresses)**
```bash
python -m arachne.simulator.enrich_infra
```

**Inject fraud rings (defined by shared infrastructure and burst in activity)**
```bash
python -m arachne.simulator.inject_rings
```

---

### 5) Load into Neo4j
```bash
python -m arachne.graph_load.load_bronze
```

---

## Running graph analytics in Neo4j Browser

Arachne builds a person-to-person linkage edges from shared infrastructure entities and runs community (fraud ring) detection.

A full query instruction and investigative workflow are documented here:

**docs/investigation.md**

---

## Example outputs (from current run)

### Most suspicious communities (multiple persons)

Fraud density by detected community (community_id_strong):

- community 228: 66 people, 1828 tx, 247 fraud (fraud_rate 0.1351)

- community 225: 56 people, 1491 tx, 190 fraud (fraud_rate 0.1274)

- community 35: 137 people, 3561 tx, 415 fraud (fraud_rate 0.1165)

### Explainibility highlight (community 228)

Examples of shared artefacts binding the community:

- multiple cards shared across 4–6 people

- devices shared across 6–8 people (including a high-volume device with 27 transactions)

- addresses shared across 5–7 people

### Top suspects example (from community 228)

**tx refers to transactions**

- P001749: 74 tx, 55 fraud (fraud_rate 0.7432)

- P000738: 71 tx, 50 fraud (fraud_rate 0.7042)

---

## Current status

Still under active development with the following next planned milestones:

- Streamlit investigator console

- GDS centrality and risk scoring

- exportable fraud case files for each community

***



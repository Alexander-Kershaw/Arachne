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

## Running graph analytics in Neo4j 

Arachne builds explainable `Person↔Person` links from shared infrastructure and then runs Leiden community detection using Neo4j Graph Data Science (GDS).

### 1) Build linkage edges, strong links, and communities

From the repo root:

```bash
python scripts/run_cypher.py \
  cypher/build_links_device.cypher \
  cypher/build_links_ip.cypher \
  cypher/build_links_card.cypher \
  cypher/build_links_address.cypher \
  cypher/build_strong_links.cypher \
  cypher/run_gds.cypher
```

This serve to:

- create/extend LINKED_TO relationships between people with shared infra (with evidence counts)

- rebuild STRONG_LINK relationships (default threshold: w >= 30)

- project STRONG_LINK into GDS as an undirected weighted graph

- write community_id_strong onto :Person nodes via Leiden


---

## Investigator console

open the investigator console from root:

```bash
streamlit run src/arachne/app/investigator.py
```

**Recommended demo inputs:**

- community_id_strong = 228

- person_id = P001749

**The console supports:**

- top suspicious communities by fraud density

- community explorer (shared cards/devices/addresses/IPs)

- top suspects within a community

- neighbour evidence for a selected suspect

- case export (copy/download as markdown)


***



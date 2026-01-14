***

# Investigation: Arachne

***
This document serves to demonstrate how to use Arachne's Neo4j graph database to investigate suspected fraud rings.

All queries are intended to be run in Neo4j Browser.

---

## Graph entities

**Nodes**
- `:Person {person_id}`
- `:Transaction {tx_id, ts, amount, currency, is_fraud}`
- `:Device {device_id}`
- `:IP {ip}`
- `:Card {card_hash}`
- `:Address {address_hash}`
- `:Merchant {merchant_id, mcc}`

**Relationships**
- `(Person)-[:MADE]->(Transaction)`
- `(Transaction)-[:USED_DEVICE]->(Device)`
- `(Transaction)-[:FROM_IP]->(IP)`
- `(Transaction)-[:PAID_WITH]->(Card)`
- `(Transaction)-[:BILLED_TO]->(Address)`
- `(Transaction)-[:TO_MERCHANT]->(Merchant)`
- `(Person)-[:LINKED_TO {w, shared_device, shared_ip, shared_card, shared_address}]->(Person)`

---

## Step 1: Find suspicious communities (fraud density)

### Objective: identify communities with unusually high fraud transaction share

```cypher
MATCH (p:Person)-[:MADE]->(t:Transaction)
WHERE p.community_id_strong IS NOT NULL
WITH p.community_id_strong AS community,
     count(DISTINCT p) AS people_count,
     count(t) AS tx_total,
     sum(CASE WHEN t.is_fraud = 1 THEN 1 ELSE 0 END) AS tx_fraud
WHERE people_count >= 5
RETURN community,
       people_count,
       tx_total,
       tx_fraud,
       round(1.0 * tx_fraud / tx_total, 4) AS fraud_rate
ORDER BY fraud_rate DESC, tx_fraud DESC
LIMIT 10;
```

Example of the output (individual results may differ): 

- community 228: 66 people, 1828 tx, 247 fraud, fraud_rate 0.1351

- community 225: 56 people, 1491 tx, 190 fraud, fraud_rate 0.1274

---

## Step 2: Case file simmary for a selected community (example here: community 228)

### Objective: generate a single case summary for a fraud investigation

```cypher
MATCH (p:Person)
WHERE p.community_id_strong = 228
WITH collect(p) AS members
CALL {
  WITH members
  UNWIND members AS p
  MATCH (p)-[:MADE]->(t:Transaction)
  RETURN count(DISTINCT p) AS people_count,
         count(t) AS tx_total,
         sum(CASE WHEN t.is_fraud = 1 THEN 1 ELSE 0 END) AS tx_fraud
}
CALL {
  WITH members
  UNWIND members AS p
  MATCH (p)-[:MADE]->(t:Transaction)
  WITH p, count(t) AS tx_total, sum(CASE WHEN t.is_fraud = 1 THEN 1 ELSE 0 END) AS tx_fraud
  RETURN collect({
    person_id: p.person_id,
    tx_total: tx_total,
    tx_fraud: tx_fraud,
    fraud_rate: round(1.0 * tx_fraud / tx_total, 4)
  })[0..10] AS top_suspects
}
RETURN
  people_count,
  tx_total,
  tx_fraud,
  round(1.0 * tx_fraud / tx_total, 4) AS fraud_rate,
  top_suspects;
```

---

## Step 3: Explainability 

### Objective: demonstrate what shared infrastructure artifacts are binding members of the community together

***
#### SHARED CARDS

```cypher
MATCH (p:Person)-[:MADE]->(:Transaction)-[:PAID_WITH]->(c:Card)
WHERE p.community_id_strong = 228
RETURN c.card_hash AS card_hash,
       count(DISTINCT p) AS people_count,
       count(*) AS tx_count
ORDER BY people_count DESC, tx_count DESC
LIMIT 15;
```

***
#### SHARED DEVICES
```cypher
MATCH (p:Person)-[:MADE]->(:Transaction)-[:USED_DEVICE]->(d:Device)
WHERE p.community_id_strong = 228
RETURN d.device_id AS device_id,
       count(DISTINCT p) AS people_count,
       count(*) AS tx_count
ORDER BY people_count DESC, tx_count DESC
LIMIT 15;
```
***

#### SHARED ADDRESSES

```cypher 
MATCH (p:Person)-[:MADE]->(:Transaction)-[:BILLED_TO]->(a:Address)
WHERE p.community_id_strong = 228
RETURN a.address_hash AS address_hash,
       count(DISTINCT p) AS people_count,
       count(*) AS tx_count
ORDER BY people_count DESC, tx_count DESC
LIMIT 15;
```

***

#### SHARED IPs

```cypher
MATCH (p:Person)-[:MADE]->(:Transaction)-[:FROM_IP]->(ip:IP)
WHERE p.community_id_strong = 228
RETURN ip.ip AS ip,
       count(DISTINCT p) AS people_count,
       count(*) AS tx_count
ORDER BY people_count DESC, tx_count DESC
LIMIT 15;
```

*** 
---

## STEP 4: Identify most prominent suspects within the community

```cypher
MATCH (p:Person)-[:MADE]->(t:Transaction)
WHERE p.community_id_strong = 228
WITH p,
     count(t) AS tx_total,
     sum(CASE WHEN t.is_fraud = 1 THEN 1 ELSE 0 END) AS tx_fraud
RETURN p.person_id AS person_id,
       tx_total,
       tx_fraud,
       round(1.0 * tx_fraud / tx_total, 4) AS fraud_rate
ORDER BY tx_fraud DESC, fraud_rate DESC, tx_total DESC
LIMIT 20;
```

---

## STEP 5: Explain why a suspect is linked to others (example suspect: P001749)

```cypher
MATCH (p:Person {person_id: "P001749"})-[r:LINKED_TO]-(q:Person)
RETURN q.person_id AS linked_person,
       r.w AS weight,
       r.shared_device AS shared_device,
       r.shared_card AS shared_card,
       r.shared_address AS shared_address,
       r.shared_ip AS shared_ip
ORDER BY weight DESC
LIMIT 20;
```

#### How to interpet this:

- Elevated weights are typically motivated by repeated shared devices, cards, addesses... across transactions.

- Supports a defensible dececion: "Flagged due to shared infrastructure with know suspicious accounts".

***


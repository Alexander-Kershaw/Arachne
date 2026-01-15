// Build LINKED_TO from shared cards (strong signal, tight cap)

MATCH (c:Card)<-[:PAID_WITH]-(t:Transaction)<-[:MADE]-(p:Person)
WITH c, collect(DISTINCT p) AS people
WITH c, people, size(people) AS n
WHERE n >= 2 AND n <= 20

UNWIND people AS p1
UNWIND people AS p2
WITH p1, p2
WHERE elementId(p1) < elementId(p2)

MERGE (p1)-[r:LINKED_TO]->(p2)
ON CREATE SET
  r.shared_device = 0,
  r.shared_ip = 0,
  r.shared_card = 0,
  r.shared_address = 0,
  r.w = 0
SET r.shared_card = r.shared_card + 1,
    r.w = r.w + 6;

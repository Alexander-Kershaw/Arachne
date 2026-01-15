// Build LINKED_TO from shared devices (capped to avoid super-shared explosions)

MATCH (d:Device)<-[:USED_DEVICE]-(t:Transaction)<-[:MADE]-(p:Person)
WITH d, collect(DISTINCT p) AS people
WITH d, people, size(people) AS n
WHERE n >= 2 AND n <= 50

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
SET r.shared_device = r.shared_device + 1,
    r.w = r.w + 5;

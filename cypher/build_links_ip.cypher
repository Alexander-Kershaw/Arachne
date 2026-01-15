// Build LINKED_TO from shared IPs (tighter cap)

MATCH (ip:IP)<-[:FROM_IP]-(t:Transaction)<-[:MADE]-(p:Person)
WITH ip, collect(DISTINCT p) AS people
WITH ip, people, size(people) AS n
WHERE n >= 2 AND n <= 30

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
SET r.shared_ip = r.shared_ip + 1,
    r.w = r.w + 2;

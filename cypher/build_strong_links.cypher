// Rebuild STRONG_LINK edges from LINKED_TO
// Threshold chosen empirically to avoid mega-communities.

MATCH (:Person)-[r:STRONG_LINK]-(:Person)
DELETE r;

MATCH (p1:Person)-[r:LINKED_TO]->(p2:Person)
WHERE r.w >= 30
MERGE (p1)-[s:STRONG_LINK]->(p2)
SET s.w = r.w;

// Project STRONG_LINK as UNDIRECTED and run Leiden community detection

CALL gds.graph.drop('person_links_strong', false) YIELD graphName;

CALL gds.graph.project(
  'person_links_strong',
  'Person',
  {
    STRONG_LINK: {
      type: 'STRONG_LINK',
      orientation: 'UNDIRECTED',
      properties: 'w'
    }
  }
);

CALL gds.leiden.write(
  'person_links_strong',
  {
    relationshipWeightProperty: 'w',
    writeProperty: 'community_id_strong'
  }
)
YIELD communityCount, modularity, ranLevels, nodePropertiesWritten
RETURN communityCount, modularity, ranLevels, nodePropertiesWritten;

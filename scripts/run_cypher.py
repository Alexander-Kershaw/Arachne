from __future__ import annotations

import os
import sys
from pathlib import Path

from neo4j import GraphDatabase


def read_cypher(path: Path) -> str:
    txt = path.read_text(encoding="utf-8")
    return txt.strip()


def split_statements(cypher: str) -> list[str]:

    parts = [p.strip() for p in cypher.split(";")]
    return [p for p in parts if p]


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_cypher.py <file1.cypher> [file2.cypher ...]", file=sys.stderr)
        return 2

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password123")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    files = [Path(p) for p in sys.argv[1:]]
    for f in files:
        if not f.exists():
            print(f"File not found: {f}", file=sys.stderr)
            return 2

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
        with driver.session(database=database) as session:
            for f in files:
                cypher = read_cypher(f)
                statements = split_statements(cypher)

                print(f"\n==> {f} ({len(statements)} statements)")
                for i, stmt in enumerate(statements, start=1):
                    # Neo4j expects a full statement, no trailing ';'
                    try:
                        session.run(stmt).consume()
                    except Exception as e:
                        print(f"\nERROR in {f} statement #{i}:\n{stmt}\n", file=sys.stderr)
                        raise

        print("\nAll cypher executed successfully.")
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path
from neo4j import GraphDatabase # importing neo4j driver with graph database support


ROOT = Path(__file__).resolve().parents[1]
CYPHER_DIR = ROOT / "cypher"

# List of cypher files to execute in order
CYPHER_FILES = [
    "constraints.cypher",
    "indexes.cypher",
]


def run_cypher_file(driver: GraphDatabase.driver, cypher_path: Path) -> None:
    text = cypher_path.read_text(encoding="utf-8").strip()
    if not text:
        print(f"SKIP empty: {cypher_path.name}")
        return

    # naive split on semicolons to allow multiple statements per file
    statements = [s.strip() for s in text.split(";") if s.strip()]

    with driver.session(database="neo4j") as session:
        for stmt in statements:
            session.run(stmt)

    print(f"OK: {cypher_path.name} ({len(statements)} statements)")


def main() -> None:
    # Match configs/arachne.example.yml defaults
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "password123"

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
        print("Successfully Connected to Neo4j")

        for fname in CYPHER_FILES:
            path = CYPHER_DIR / fname
            if not path.exists():
                raise FileNotFoundError(f"Missing cypher file: {path}")
            run_cypher_file(driver, path)

        # Check GDS installation
        with driver.session(database="neo4j") as session:
            gds_ok = session.run("RETURN gds.version() AS v").single()
            print(f"GDS version: {gds_ok['v']}")

    finally:
        driver.close()


if __name__ == "__main__":
    main()

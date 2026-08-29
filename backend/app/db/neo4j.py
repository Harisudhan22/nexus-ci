from neo4j import GraphDatabase
from app.core.config import settings

class Neo4jSessionManager:
    def __init__(self):
        self._driver = None

    def connect(self):
        if not self._driver:
            try:
                self._driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
                )
            except Exception as e:
                print(f"Failed to connect to Neo4j at {settings.NEO4J_URI}: {e}")
                self._driver = None

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    def get_session(self):
        self.connect()
        if not self._driver:
            raise RuntimeError("Neo4j driver is not connected.")
        return self._driver.session()

neo4j_client = Neo4jSessionManager()

def get_neo4j():
    try:
        session = neo4j_client.get_session()
        try:
            yield session
        finally:
            session.close()
    except Exception as e:
        print(f"Neo4j Session Error: {e}")
        # Allow running without Neo4j for mock or fallback if connection fails
        yield None

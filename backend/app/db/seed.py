import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.seed_historical import seed_all

def seed_databases():
    """Idempotent seed wrapper for NEXUS-CI."""
    seed_all()

if __name__ == "__main__":
    seed_databases()

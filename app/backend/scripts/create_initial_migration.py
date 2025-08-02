#!/usr/bin/env python3
"""
Script to create initial database migration.
"""

import os
import sys
from pathlib import Path

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic.config import Config
from alembic import command


def create_initial_migration():
    """Create the initial migration with all models."""
    
    # Get alembic config
    alembic_cfg = Config("alembic.ini")
    
    # Create initial migration
    print("Creating initial migration...")
    command.revision(
        alembic_cfg, 
        message="Initial migration - all models",
        autogenerate=True
    )
    
    print("Initial migration created successfully!")
    print("\nTo apply the migration, run:")
    print("alembic upgrade head")


if __name__ == "__main__":
    create_initial_migration()
#!/usr/bin/env python3
"""
Script to create database tables directly using SQLAlchemy
"""
import asyncio
from sqlalchemy import create_engine
from app.models.base import Base
from app.models import *  # Import all models

# Database URL
DATABASE_URL = "postgresql://solana_mafia:password@localhost:5432/solana_mafia_db"

def main():
    """Create all tables in the database"""
    print("Creating database tables...")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("✅ All tables created successfully!")
    
    # Print table names
    print("\nCreated tables:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")

if __name__ == "__main__":
    main()
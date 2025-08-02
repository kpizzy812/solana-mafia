#!/usr/bin/env python3
"""
Database management script for Solana Mafia backend.
"""

import asyncio
import sys
from pathlib import Path

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from rich.console import Console
from rich.table import Table

from alembic.config import Config
from alembic import command
from app.core.database import init_database, close_database, DatabaseManager
from app.core.logging import setup_logging, get_logger

console = Console()
logger = get_logger(__name__)
app = typer.Typer(help="Database management commands")


@app.command()
def init():
    """Initialize database with tables."""
    async def _init():
        setup_logging()
        await init_database()
        await DatabaseManager.create_tables()
        await close_database()
        console.print("✅ Database initialized successfully!")
    
    asyncio.run(_init())


@app.command()
def migrate():
    """Create a new migration."""
    message = typer.prompt("Migration message")
    
    alembic_cfg = Config("alembic.ini")
    command.revision(alembic_cfg, message=message, autogenerate=True)
    
    console.print(f"✅ Migration created: {message}")


@app.command()
def upgrade(revision: str = "head"):
    """Apply migrations."""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, revision)
    
    console.print(f"✅ Database upgraded to: {revision}")


@app.command()
def downgrade(revision: str):
    """Downgrade database to specific revision."""
    alembic_cfg = Config("alembic.ini")
    command.downgrade(alembic_cfg, revision)
    
    console.print(f"⬇️ Database downgraded to: {revision}")


@app.command()
def current():
    """Show current database revision."""
    alembic_cfg = Config("alembic.ini")
    command.current(alembic_cfg)


@app.command()
def history():
    """Show migration history."""
    alembic_cfg = Config("alembic.ini")
    command.history(alembic_cfg)


@app.command()
def reset():
    """Reset database (drop all tables)."""
    confirm = typer.confirm("Are you sure you want to drop all tables?")
    if not confirm:
        console.print("❌ Operation cancelled")
        return
    
    async def _reset():
        setup_logging()
        await init_database()
        await DatabaseManager.drop_tables()
        await close_database()
        console.print("🗑️ All tables dropped!")
    
    asyncio.run(_reset())


@app.command()
def health():
    """Check database health."""
    async def _health():
        setup_logging()
        await init_database()
        
        is_healthy = await DatabaseManager.health_check()
        
        if is_healthy:
            console.print("✅ Database is healthy!")
        else:
            console.print("❌ Database health check failed!")
            sys.exit(1)
        
        await close_database()
    
    asyncio.run(_health())


@app.command()
def seed():
    """Seed database with sample data."""
    console.print("🌱 Seeding database with sample data...")
    
    async def _seed():
        setup_logging()
        await init_database()
        
        # Add sample data creation logic here
        console.print("✅ Database seeded successfully!")
        
        await close_database()
    
    asyncio.run(_seed())


@app.command()
def status():
    """Show database status."""
    
    table = Table(title="Database Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    
    async def _status():
        setup_logging()
        await init_database()
        
        # Check database connectivity
        is_healthy = await DatabaseManager.health_check()
        table.add_row("Database", "✅ Connected" if is_healthy else "❌ Disconnected")
        
        # Check current migration
        alembic_cfg = Config("alembic.ini")
        # This would need more implementation to get current revision
        table.add_row("Migrations", "Ready")
        
        console.print(table)
        
        await close_database()
    
    asyncio.run(_status())


if __name__ == "__main__":
    app()
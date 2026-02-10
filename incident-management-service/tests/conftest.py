"""Shared test fixtures for incident-management-service.

Set DATABASE_URL *before* app.main is imported so the module-level
create_engine() call targets SQLite instead of PostgreSQL.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.pop("DATABASE_PASSWORD", None)
os.environ.pop("DATABASE_PASSWORD_FILE", None)

"""Minimal additive migrations for SQLite.

Base.metadata.create_all() creates missing *tables* but never alters existing
ones, so a database created before a column was added keeps the old shape.
This adds any missing columns in place, which is all this project needs.
Replace with Alembic once changes stop being purely additive.
"""

from sqlalchemy import Engine, inspect, text

# table -> column -> DDL fragment used to add it
ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "images": {
        "is_public": "BOOLEAN NOT NULL DEFAULT 0",
        "published_at": "DATETIME",
    },
}


def run(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table, columns in ADDED_COLUMNS.items():
            if table not in existing_tables:
                continue  # create_all() will build it with every column
            present = {c["name"] for c in inspector.get_columns(table)}
            for column, ddl in columns.items():
                if column not in present:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))

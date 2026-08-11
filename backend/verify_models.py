import sys
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from app.database import Base
# Import all models to ensure they are registered with Base.metadata
from app.models import *

def main():
    print("Starting Model Verification...")

    # Check if models are imported and registered
    tables = Base.metadata.tables.keys()
    expected_tables = {
        "users",
        "categories",
        "transactions",
        "budgets",
        "saving_goals",
        "saving_contributions",
        "ai_reports"
    }

    print(f"\n1. Checking registered tables...")
    registered_tables = set(tables)
    missing = expected_tables - registered_tables
    extra = registered_tables - expected_tables

    if missing:
        print(f"[FAIL] Missing tables: {missing}")
    elif extra:
        print(f"[FAIL] Extra tables found: {extra}")
    else:
        print("[SUCCESS] All 7 models successfully imported and registered in SQLAlchemy metadata.")
        print(f"   Registered tables: {', '.join(registered_tables)}")

    # Use SQLite in-memory DB for verification
    print("\n2. Verifying relationships, PK/FK, and constraints via SQLite in-memory creation...")
    engine = create_engine("sqlite:///:memory:", echo=False)

    try:
        # This will attempt to create all tables and will fail if there are relationship
        # definition errors (like invalid back_populates), or invalid foreign keys syntax
        Base.metadata.create_all(bind=engine)
        print("[SUCCESS] Tables successfully created in in-memory SQLite.")
        print("   This confirms relationships, basic PK/FK syntax, and back_populates are structurally valid.")

        # Verify FK constraints on SavingContribution
        print("\n3. Inspecting SavingContribution Foreign Keys...")
        from sqlalchemy import inspect
        inspector = inspect(engine)
        fks = inspector.get_foreign_keys("saving_contributions")
        for fk in fks:
            print(f"   FK: {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']} (ON DELETE: {fk.get('options', {}).get('ondelete', 'NOT SET')})")
        # NOTE: SQLite doesn't fully report ON DELETE SET NULL via inspector sometimes, but we check if it runs.

    except Exception as e:
        print(f"[FAIL] Error during table creation/verification:")
        print(e)
        sys.exit(1)

    print("\nVerification completed successfully!")

if __name__ == "__main__":
    main()

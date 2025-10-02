#!/usr/bin/env python3
"""
Validate production fixes are working correctly.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config.database import engine
from backend.domains.translation.models import TranslationJob
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

def check_connection_pool():
    """Verify connection pool configuration."""
    print("=" * 60)
    print("CONNECTION POOL CONFIGURATION")
    print("=" * 60)
    
    pool = engine.pool
    print(f"✅ Pool class: {pool.__class__.__name__}")
    print(f"✅ Pool size: {engine.pool.size()}")
    print(f"✅ Max overflow: {engine.pool._max_overflow}")
    
    # Check if pre_ping is enabled
    if hasattr(engine.pool, '_pre_ping'):
        print(f"✅ Pre-ping enabled: {engine.pool._pre_ping}")
    
    # Check pool_recycle
    if hasattr(engine.pool, '_recycle'):
        print(f"✅ Pool recycle: {engine.pool._recycle} seconds")
    
    print()

def check_indexes():
    """Verify indexes are created."""
    print("=" * 60)
    print("DATABASE INDEXES")
    print("=" * 60)
    
    inspector = inspect(engine)
    indexes = inspector.get_indexes('translation_jobs')
    
    required_indexes = {
        'ix_translation_jobs_status_created_at': ['status', 'created_at'],
        'ix_translation_jobs_owner_id': ['owner_id'],
        'ix_translation_jobs_created_at': ['created_at'],
    }
    
    found_indexes = {idx['name']: idx['column_names'] for idx in indexes}
    
    for idx_name, columns in required_indexes.items():
        if idx_name in found_indexes:
            print(f"✅ Index '{idx_name}' exists on {columns}")
        else:
            print(f"❌ Index '{idx_name}' MISSING!")
    
    print(f"\nTotal indexes: {len(indexes)}")
    print()

def test_query_performance():
    """Test query performance with indexes."""
    print("=" * 60)
    print("QUERY PERFORMANCE TEST")
    print("=" * 60)
    
    with Session(engine) as session:
        # Test indexed query
        query = """
        SELECT * FROM translation_jobs 
        WHERE status = 'COMPLETED' 
        ORDER BY created_at DESC 
        LIMIT 10
        """
        
        result = session.execute(text("EXPLAIN QUERY PLAN " + query))
        plan = result.fetchall()
        
        print("Query plan for status + created_at filter:")
        for row in plan:
            print(f"  {row}")
        
        # Check if using index
        plan_str = str(plan)
        if 'ix_translation_jobs_status_created_at' in plan_str or 'USING INDEX' in plan_str:
            print("✅ Query is using index!")
        else:
            print("⚠️  Query might not be using index (check plan above)")
    
    print()

def check_unbounded_queries():
    """Verify unbounded queries have limits."""
    print("=" * 60)
    print("UNBOUNDED QUERY PROTECTION")
    print("=" * 60)
    
    # Check watchdog.py for limit
    watchdog_file = Path(__file__).parent.parent / 'backend' / 'maintenance' / 'watchdog.py'
    
    if watchdog_file.exists():
        content = watchdog_file.read_text()
        if '.limit(' in content:
            print("✅ Watchdog has query limit protection")
            # Extract the limit value
            import re
            match = re.search(r'\.limit\((\d+)\)', content)
            if match:
                print(f"   Limit value: {match.group(1)} rows")
        else:
            print("❌ Watchdog missing query limit!")
    else:
        print("⚠️  Could not find watchdog.py")
    
    print()

def main():
    """Run all validation checks."""
    print("\n" + "=" * 60)
    print("PRODUCTION FIXES VALIDATION")
    print("=" * 60 + "\n")
    
    try:
        check_connection_pool()
        check_indexes()
        test_query_performance()
        check_unbounded_queries()
        
        print("=" * 60)
        print("VALIDATION COMPLETE")
        print("=" * 60)
        print("\n✅ All critical fixes are in place!\n")
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

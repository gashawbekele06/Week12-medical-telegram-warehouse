"""Test database connection and queries"""
from api.database import get_db
from sqlalchemy import text

db = next(get_db())

try:
    # Test 1: Basic connection
    result = db.execute(text("SELECT 1")).fetchone()
    print(f"✓ Database connection: {result}")
    
    # Test 2: Check if table exists
    result = db.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public_public_marts'
    """)).fetchall()
    print(f"✓ Tables in public_public_marts: {[r[0] for r in result]}")
    
    # Test 3: Try the top products query
    query = text("""
        SELECT word, COUNT(*) AS count
        FROM (
            SELECT UNNEST(STRING_TO_ARRAY(LOWER(message_text), ' ')) AS word
            FROM public_public_marts.fct_messages
            WHERE message_text IS NOT NULL
        ) words
        WHERE LENGTH(word) > 3
          AND word NOT IN ('the', 'and', 'for', 'with', 'from', 'this', 'that')
        GROUP BY word
        ORDER BY count DESC
        LIMIT 10
    """)
    result = db.execute(query).fetchall()
    print(f"✓ Top products query returned {len(result)} rows")
    for r in result[:3]:
        print(f"  - {r[0]}: {r[1]}")
        
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
finally:
    db.close()

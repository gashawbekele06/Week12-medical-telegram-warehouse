"""Find where fct_messages actually is"""
from api.database import get_db
from sqlalchemy import text

db = next(get_db())

try:
    # Find all tables with 'fct_messages' in the name
    result = db.execute(text("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_name LIKE '%fct_messages%'
        ORDER BY table_schema, table_name
    """)).fetchall()
    
    print("Tables matching 'fct_messages':")
    for r in result:
        print(f"  - {r[0]}.{r[1]}")
    
    # Find all schemas
    result = db.execute(text("""
        SELECT DISTINCT table_schema 
        FROM information_schema.tables 
        WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        ORDER BY table_schema
    """)).fetchall()
    
    print("\nAll schemas:")
    for r in result:
        print(f"  - {r[0]}")
        
    # Find all tables in public schema
    result = db.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)).fetchall()
    
    print("\nTables in 'public' schema:")
    for r in result:
        print(f"  - {r[0]}")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()

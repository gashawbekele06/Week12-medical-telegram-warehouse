"""Test visual content query"""
from api.database import get_db
from sqlalchemy import text

db = next(get_db())

try:
    query = text("""
        SELECT 
            c.channel_name,
            COUNT(y.message_id) AS total_images,
            SUM(CASE WHEN y.image_category = 'promotional' THEN 1 ELSE 0 END) AS promotional_count,
            SUM(CASE WHEN y.image_category = 'product_display' THEN 1 ELSE 0 END) AS product_display_count,
            SUM(CASE WHEN y.image_category = 'lifestyle' THEN 1 ELSE 0 END) AS lifestyle_count,
            SUM(CASE WHEN y.image_category = 'other' THEN 1 ELSE 0 END) AS other_count,
            ROUND(
                CASE WHEN COUNT(f.message_id) > 0 
                     THEN COUNT(y.message_id)::numeric / COUNT(f.message_id) * 100 
                     ELSE 0 END,
                1
            ) AS visual_percentage
        FROM public.fct_messages f
        JOIN public.dim_channels c ON f.channel_key = c.channel_key
        LEFT JOIN public_public_marts.fct_image_detections y 
            ON f.message_id::text = y.message_id
        GROUP BY c.channel_name
        ORDER BY total_images DESC
    """)
    result = db.execute(query).fetchall()
    print(f"✓ Query returned {len(result)} rows")
    for r in result[:3]:
        print(f"  - {r[0]}: {r[1]} images")
        
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
finally:
    db.close()

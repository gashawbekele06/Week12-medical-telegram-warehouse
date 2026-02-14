from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from api.database import get_db
from api.schemas import (
    TopProduct, ChannelActivityItem, MessageSearchResult, VisualContentStats
)

router = APIRouter(prefix="/api", tags=["analytics"])

@router.get("/reports/top-products", response_model=List[TopProduct])
def get_top_products(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Top mentioned words/terms across all messages"""
    query = text("""
        SELECT word, COUNT(*) AS count
        FROM (
            SELECT UNNEST(STRING_TO_ARRAY(LOWER(message_text), ' ')) AS word
            FROM public.fct_messages
            WHERE message_text IS NOT NULL
        ) words
        WHERE LENGTH(word) > 3
          AND word NOT IN ('the', 'and', 'for', 'with', 'from', 'this', 'that')
        GROUP BY word
        ORDER BY count DESC
        LIMIT :limit
    """)
    result = db.execute(query, {"limit": limit}).fetchall()
    if not result:
        raise HTTPException(404, "No terms found")
    return [{"term": r[0], "count": r[1]} for r in result]

@router.get("/channels/{channel_name}/activity", response_model=List[ChannelActivityItem])
def get_channel_activity(
    channel_name: str,
    db: Session = Depends(get_db)
):
    """Daily posting activity for a channel"""
    query = text("""
        SELECT 
            DATE(message_timestamp) AS post_date,
            COUNT(*) AS message_count,
            ROUND(AVG(view_count), 1) AS avg_views
        FROM public.fct_messages f
        JOIN public.dim_channels c ON f.channel_key = c.channel_key
        WHERE c.channel_name ILIKE :channel_name
        GROUP BY post_date
        ORDER BY post_date DESC
        LIMIT 30
    """)
    result = db.execute(query, {"channel_name": f"%{channel_name}%"}).fetchall()
    if not result:
        raise HTTPException(404, f"No activity found for channel '{channel_name}'")
    return [{"post_date": r[0], "message_count": r[1], "avg_views": r[2]} for r in result]

@router.get("/search/messages", response_model=List[MessageSearchResult])
def search_messages(
    query: str = Query(..., min_length=3),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search messages containing a keyword"""
    search_term = f"%{query.lower()}%"
    sql = text("""
        SELECT 
            f.message_id,
            c.channel_name,
            f.message_text,
            f.view_count,
            DATE(f.message_timestamp) AS message_timestamp
        FROM public.fct_messages f
        JOIN public.dim_channels c ON f.channel_key = c.channel_key
        WHERE LOWER(f.message_text) LIKE :term
        ORDER BY f.view_count DESC NULLS LAST
        LIMIT :limit
    """)
    result = db.execute(sql, {"term": search_term, "limit": limit}).fetchall()
    if not result:
        raise HTTPException(404, f"No messages found for query '{query}'")
    return [
        {
            "message_id": r[0],
            "channel_name": r[1],
            "message_text": r[2],
            "view_count": r[3],
            "message_timestamp": r[4]
        }
        for r in result
    ]

@router.get("/reports/visual-content", response_model=List[VisualContentStats])
def get_visual_content_stats(db: Session = Depends(get_db)):
    """Image usage statistics per channel"""
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
            ON f.message_id = y.message_id::bigint
        GROUP BY c.channel_name
        ORDER BY total_images DESC
    """)
    result = db.execute(query).fetchall()
    return [
        {
            "channel_name": r[0],
            "total_images": r[1] or 0,
            "promotional_count": r[2] or 0,
            "product_display_count": r[3] or 0,
            "lifestyle_count": r[4] or 0,
            "other_count": r[5] or 0,
            "visual_percentage": r[6] or 0.0
        }
        for r in result
    ]
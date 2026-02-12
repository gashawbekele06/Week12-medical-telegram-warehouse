{{ config(materialized='table') }}

SELECT
    ROW_NUMBER() OVER () AS channel_key,
    channel_username AS channel_name,
    CASE 
        WHEN channel_username ILIKE '%chemed%' THEN 'Medical'
        WHEN channel_username ILIKE '%lobelia%' THEN 'Cosmetics'
        WHEN channel_username ILIKE '%tikvah%' OR channel_username ILIKE '%pharma%' THEN 'Pharmaceutical'
        ELSE 'Other'
    END AS channel_type,
    MIN(message_timestamp) AS first_post_date,
    MAX(message_timestamp) AS last_post_date,
    COUNT(*) AS total_posts,
    AVG(view_count) AS avg_views
FROM {{ ref('stg_telegram_messages') }}
GROUP BY channel_username
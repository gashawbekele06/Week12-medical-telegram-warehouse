{{ config(materialized='view') }}

WITH cleaned AS (
    SELECT
        message_id::BIGINT                      AS message_id,
        channel_username::TEXT                  AS channel_username,
        channel_title::TEXT                     AS channel_title,
        date::TIMESTAMP WITH TIME ZONE          AS message_timestamp,
        text::TEXT                              AS message_text,
        views::INTEGER                          AS view_count,
        forwards::INTEGER                       AS forward_count,
        has_media::BOOLEAN                      AS has_media,
        image_path::TEXT                        AS image_path,
        loaded_at::TIMESTAMP WITH TIME ZONE     AS loaded_at
    FROM raw.telegram_messages
    WHERE message_id IS NOT NULL
      AND channel_username IS NOT NULL
      AND date IS NOT NULL                      -- ← change to 'date' (original column)
      AND date <= CURRENT_TIMESTAMP             -- ← change to 'date'
)

SELECT
    *,
    LENGTH(message_text)                        AS message_length,
    CASE WHEN image_path IS NOT NULL THEN TRUE ELSE FALSE END AS has_image_flag,
    TRIM(REGEXP_REPLACE(message_text, '\s+', ' ', 'g')) AS cleaned_text
FROM cleaned
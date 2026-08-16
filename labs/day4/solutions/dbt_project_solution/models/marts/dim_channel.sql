select
    channel_id,
    channel_name,
    is_digital
from {{ ref('stg_channels') }}

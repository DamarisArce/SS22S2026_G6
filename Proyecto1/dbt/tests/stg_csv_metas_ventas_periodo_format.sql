select periodo, _etl_row_number
from {{ source('raw', 'csv_metas_ventas') }}
where nullif(btrim(periodo), '') is not null
  and btrim(periodo) !~ '^[0-9]{4}-(0[1-9]|1[0-2])$'

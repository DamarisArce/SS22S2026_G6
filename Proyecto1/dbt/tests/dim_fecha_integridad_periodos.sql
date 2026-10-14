select periodos.periodo, 'periodo_mensual_ausente_o_no_es_primer_dia' as violation
from {{ ref('int_ventas_mensuales_sucursal') }} as periodos
left join {{ ref('dim_fecha') }} as calendario
    on calendario.fecha = periodos.periodo
where periodos.periodo is null
   or calendario.fecha is null
   or periodos.periodo is distinct from date_trunc('month', periodos.periodo)::date

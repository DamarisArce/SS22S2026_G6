{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {%- set requested_schema = custom_schema_name | trim -%}
        {%- if requested_schema in ['staging', 'intermediate', 'marts'] -%}
            {{ requested_schema }}
        {%- elif requested_schema == 'dbt_test__audit'
            and node is not none
            and node.resource_type == 'test'
            and target.name == 'dev'
            and target.schema == 'staging' -%}
            {{ target.schema }}
        {%- else -%}
            {{ exceptions.raise_compiler_error(
                "Schema no autorizado por SG-Food dbt: " ~ requested_schema
            ) }}
        {%- endif -%}
    {%- endif -%}
{%- endmacro %}

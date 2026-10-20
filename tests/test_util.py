import pytest
from sqlglot.errors import ParseError

from sql_optimizer_app.util import (
    COMMUNITY_DIALECTS,
    RULE_MAPPING,
    SAMPLE_QUERY,
    SAMPLE_SCHEMA,
    available_dialects,
    convert_sql,
    dialect_label,
    parse_schema,
)


def test_available_dialects_include_generic_and_community():
    dialects = available_dialects()
    assert dialects[0] == ""
    assert {"snowflake", "tsql", "duckdb"} <= set(dialects)
    assert COMMUNITY_DIALECTS <= set(dialects)


def test_dialect_label():
    assert dialect_label("") == "(generic sqlglot)"
    assert dialect_label("singlestore") == "singlestore (community)"
    assert dialect_label("snowflake") == "snowflake"
    assert dialect_label("some_plugin") == "some_plugin (plugin)"


def test_transpile_uses_target_dialect():
    sql = convert_sql(
        "SELECT TOP 5 a FROM t", source_dialect="tsql", target_dialect="duckdb", rules=[]
    )
    assert "LIMIT 5" in sql
    assert "TOP" not in sql


def test_optimize_sample_query_keeps_ctes():
    rules = [r for name, r in RULE_MAPPING.items() if name != "quote_identifiers"]
    sql = convert_sql(SAMPLE_QUERY, rules=rules, schema=parse_schema(SAMPLE_SCHEMA))
    assert sql.startswith("WITH")
    assert "users_table.name AS name" in sql
    assert "email" not in sql  # unused columns are pruned


def test_remove_ctes_merges_them():
    sql = convert_sql(SAMPLE_QUERY, remove_ctes=True, schema=parse_schema(SAMPLE_SCHEMA))
    assert "WITH" not in sql


def test_schema_expands_star():
    schema = parse_schema('{"users_table": {"id": "int", "name": "text"}}')
    sql = convert_sql("SELECT * FROM users_table", schema=schema)
    assert '"id"' in sql and '"name"' in sql


def test_unqualified_columns_without_schema_do_not_fail():
    convert_sql("SELECT a, b FROM t JOIN u ON t.id = u.id")


def test_lint_with_sqlfmt_lowercases():
    assert "select" in convert_sql("SELECT a FROM t", rules=[], lint=True)


def test_parse_schema():
    assert parse_schema("  ") is None
    with pytest.raises(ValueError):
        parse_schema("[1, 2]")


def test_parse_error():
    with pytest.raises(ParseError):
        convert_sql("SELECT FROM WHERE (")

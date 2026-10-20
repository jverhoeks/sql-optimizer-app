import json
from collections.abc import Callable, Sequence
from importlib.metadata import entry_points

from sqlfmt.api import Mode, format_string
from sqlglot import exp, parse_one
from sqlglot.dialects import DIALECTS as BUILTIN_DIALECTS
from sqlglot.dialects.dialect import PLUGIN_GROUP_NAME
from sqlglot.optimizer import RULES, optimize

RULE_MAPPING: dict[str, Callable] = {rule.__name__: rule for rule in RULES}
BUILTIN_DIALECT_KEYS: list[str] = sorted(name.lower() for name in BUILTIN_DIALECTS)

# Dialects marked "Community" in the sqlglot README; all others are maintained by the core team.
COMMUNITY_DIALECTS: frozenset[str] = frozenset(
    {
        "dax",
        "doris",
        "dremio",
        "drill",
        "druid",
        "dune",
        "exasol",
        "fabric",
        "materialize",
        "prql",
        "risingwave",
        "singlestore",
        "solr",
        "teradata",
    }
)

SAMPLE_QUERY: str = """WITH users AS (
    SELECT *
    FROM users_table),
orders AS (
    SELECT *
    FROM orders_table),
combined AS (
    SELECT users.id, users.name, orders.order_id, orders.total
    FROM users
    JOIN orders ON users.id = orders.user_id)
SELECT combined.id, combined.name, combined.order_id, combined.total
FROM combined
"""

# Schema for SAMPLE_QUERY. Needed to expand `SELECT *` (and to prune the unused columns).
SAMPLE_SCHEMA: str = """{
  "users_table": {"id": "int", "name": "text", "email": "text"},
  "orders_table": {"order_id": "int", "user_id": "int", "total": "decimal", "created_at": "date"}
}"""


def _plugin_dialects() -> list[str]:
    """Dialects registered by third-party packages via the `sqlglot.dialects` entry point."""
    return sorted({ep.name for ep in entry_points(group=PLUGIN_GROUP_NAME)})


def available_dialects() -> list[str]:
    """
    All dialect keys usable with sqlglot: built-in (official + community) and plugins.
    The empty string is sqlglot's generic dialect.
    """
    plugins = [name for name in _plugin_dialects() if name not in BUILTIN_DIALECT_KEYS]
    return ["", *BUILTIN_DIALECT_KEYS, *plugins]


def dialect_label(dialect: str) -> str:
    if not dialect:
        return "(generic sqlglot)"
    if dialect in COMMUNITY_DIALECTS:
        return f"{dialect} (community)"
    if dialect not in BUILTIN_DIALECT_KEYS:
        return f"{dialect} (plugin)"
    return dialect


def parse_schema(schema_text: str) -> dict | None:
    """
    Parse an optional JSON schema, e.g. {"users_table": {"id": "int", "name": "text"}}.
    Returns None for empty input.
    """
    if not schema_text.strip():
        return None
    schema = json.loads(schema_text)
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a JSON object mapping tables to {column: type}.")
    return schema


def apply_optimizations(
    query: str,
    source_dialect: str = "",
    rules: Sequence[Callable] = RULES,
    remove_ctes: bool = False,
    schema: dict | None = None,
) -> exp.Expression:
    """
    Parse `query` in `source_dialect` and apply the given optimizer rules.
    With no rules the parsed AST is returned unchanged (pure transpilation).
    """
    ast = parse_one(query, dialect=source_dialect or None)
    if not rules:
        return ast
    return optimize(
        ast,
        schema=schema,
        dialect=source_dialect or None,
        rules=rules,
        leave_tables_isolated=not remove_ctes,
        # Without a schema, unqualified columns can't always be resolved; don't fail on that.
        validate_qualify_columns=schema is not None,
    )


def convert_sql(
    query: str,
    source_dialect: str = "",
    target_dialect: str = "",
    rules: Sequence[Callable] = RULES,
    remove_ctes: bool = False,
    schema: dict | None = None,
    lint: bool = False,
) -> str:
    """Optimize `query` and render it in `target_dialect`, optionally formatted with sqlfmt."""
    ast = apply_optimizations(query, source_dialect, rules, remove_ctes, schema)
    sql = ast.sql(dialect=target_dialect or None, pretty=True)
    if lint:
        sql = format_sql_with_sqlfmt(sql)
    return sql


def format_sql_with_sqlfmt(query: str) -> str:
    """
    Format a query using sqlfmt.
    """
    return format_string(query, Mode())

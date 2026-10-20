import os

import streamlit as st
from streamlit_ace import st_ace

from sql_optimizer_app.util import (
    RULE_MAPPING,
    SAMPLE_QUERY,
    SAMPLE_SCHEMA,
    available_dialects,
    convert_sql,
    dialect_label,
    parse_schema,
)

EDITOR_HEIGHT = int(os.getenv("EDITOR_HEIGHT", "500"))
FONT_SIZE = int(os.getenv("FONT_SIZE", "14"))
EDITOR_THEME = os.getenv("EDITOR_THEME", "monokai")

st.set_page_config(page_title="SQL Optimizer", page_icon="🛠️", layout="wide")

st.title("SQL Optimizer")
st.caption(
    "Optimize, transpile and lint SQL with [sqlglot](https://github.com/tobymao/sqlglot) "
    "and [sqlfmt](https://sqlfmt.com/)."
)

if "output" not in st.session_state:
    st.session_state.output = ""
    st.session_state.output_version = 0

dialects = available_dialects()


def _editor(value: str, **kwargs) -> str:
    return st_ace(
        value=value,
        height=EDITOR_HEIGHT,
        theme=EDITOR_THEME,
        language="sql",
        font_size=FONT_SIZE,
        wrap=True,
        auto_update=True,
        **kwargs,
    )


def _swap_dialects() -> None:
    st.session_state.source_dialect, st.session_state.target_dialect = (
        st.session_state.target_dialect,
        st.session_state.source_dialect,
    )


with st.sidebar:
    st.header("Options")
    selected_rules = st.multiselect(
        "Optimizer [rules](https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/optimizer.py)",
        list(RULE_MAPPING),
        default=list(RULE_MAPPING),
        help="Drop `quote_identifiers` to avoid quoting. Clear all rules to only transpile.",
    )
    remove_ctes = st.checkbox("Remove CTEs", help="Allow merging CTEs into the main query.")
    lint = st.checkbox("Lint with sqlfmt")
    schema_text = st.text_area(
        "Schema (optional JSON)",
        SAMPLE_SCHEMA,
        help="Table → column → type. Required to expand `SELECT *`; also resolves columns.",
        height=200,
    )

left, middle, right = st.columns([20, 1, 20], vertical_alignment="bottom")
with left:
    st.selectbox("Source dialect", dialects, format_func=dialect_label, key="source_dialect")
with middle:
    st.button("", icon=":material/swap_horiz:", on_click=_swap_dialects, help="Swap dialects")
with right:
    st.selectbox("Target dialect", dialects, format_func=dialect_label, key="target_dialect")

left, right = st.columns(2)
with left:
    sql_input = _editor(SAMPLE_QUERY, key="input")
with right:
    _editor(
        st.session_state.output,
        readonly=True,
        key=f"output-{st.session_state.output_version}",
    )

convert_col, download_col, _ = st.columns([2, 2, 8])
if convert_col.button("Optimize SQL", type="primary", width="stretch"):
    try:
        st.session_state.output = convert_sql(
            sql_input,
            source_dialect=st.session_state.source_dialect,
            target_dialect=st.session_state.target_dialect,
            rules=[RULE_MAPPING[rule] for rule in selected_rules],
            remove_ctes=remove_ctes,
            schema=parse_schema(schema_text),
            lint=lint,
        )
        st.session_state.output_version += 1
        st.rerun()
    except Exception as e:  # sqlglot/sqlfmt raise many error types on bad input
        st.error(f"{type(e).__name__}: {e}")

download_col.download_button(
    "Download",
    st.session_state.output,
    file_name="optimized.sql",
    mime="text/sql",
    disabled=not st.session_state.output,
    width="stretch",
)

st.caption("Based on <https://github.com/jtalmi/sql-optimizer-app/>")

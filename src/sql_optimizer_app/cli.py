import sys
from pathlib import Path

from streamlit.web import cli as stcli


def main() -> None:
    """
    Launch the Streamlit app; extra arguments are passed through to `streamlit run`.
    Binds to localhost unless `--server.address` is given.
    """
    app = Path(__file__).with_name("app.py")
    args = sys.argv[1:]
    if not any(arg.startswith("--server.address") for arg in args):
        args = ["--server.address", "localhost", *args]
    sys.argv = ["streamlit", "run", str(app), *args]
    sys.exit(stcli.main())

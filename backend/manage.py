import os
import sys
import time

import dj_database_url
import psycopg
from psycopg import sql

from dotenv import load_dotenv

from embedded_db import init_db


def _ensure_postgres_database() -> None:
    """
    Ensure the PostgreSQL database defined in DATABASE_URL exists.
    Skips when SQLite is explicitly requested via USE_SQLITE.
    """
    db_url = os.environ.get("DATABASE_URL")
    use_sqlite = os.environ.get("USE_SQLITE", "")
    if use_sqlite and use_sqlite.lower() in {"1", "true", "yes"}:
        if not db_url or db_url.startswith("sqlite"):
            return

    if not db_url:
        return

    try:
        config = dj_database_url.parse(db_url)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Warning: unable to parse DATABASE_URL ({exc}); skipping auto-create.", file=sys.stderr)
        return

    engine = (config.get("ENGINE") or "").lower()
    if "postgresql" not in engine:
        return

    target_db = config.get("NAME")
    if not target_db:
        return

    maintenance_db = os.environ.get("PG_MAINTENANCE_DB", "postgres")
    conn_kwargs = {
        "host": config.get("HOST") or None,
        "port": config.get("PORT") or None,
        "user": config.get("USER") or None,
        "password": config.get("PASSWORD") or None,
        "dbname": maintenance_db,
    }
    conn_kwargs = {k: v for k, v in conn_kwargs.items() if v is not None}

    attempts = 0
    last_error = None
    while attempts < 5:
        try:
            with psycopg.connect(**conn_kwargs) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
                    if cur.fetchone():
                        return
                    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_db)))
                    print(f"Debug: Created missing database '{target_db}'.")
            return
        except psycopg.errors.DuplicateDatabase:
            return
        except psycopg.OperationalError as exc:
            last_error = exc
            attempts += 1
            time.sleep(min(1 + attempts, 5))
    if last_error:
        print(
            f"Warning: unable to ensure database '{target_db}' exists ({last_error}).",
            file=sys.stderr,
        )


def main() -> None:
    """Run administrative tasks."""
    # Add the project root directory to the Python path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    load_dotenv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

    use_sqlite_env = os.environ.get("USE_SQLITE", "")
    database_url = os.environ.get("DATABASE_URL", "")
    use_sqlite_flag = use_sqlite_env.strip().lower() in {"1", "true", "yes", "on"}
    parsed_db_config = {}
    if database_url and not use_sqlite_flag:
        try:
            parsed_db_config = dj_database_url.parse(database_url)
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Warning: unable to parse DATABASE_URL ({exc}); using defaults.", file=sys.stderr)
            parsed_db_config = {}
    engine = (parsed_db_config.get("ENGINE") or "").lower()
    using_sqlite = False
    using_postgres = not using_sqlite and (not engine or "postgres" in engine)
    if using_postgres:
        host = parsed_db_config.get("HOST")
        port = parsed_db_config.get("PORT")
        user = parsed_db_config.get("USER")
        password = parsed_db_config.get("PASSWORD")
        name = parsed_db_config.get("NAME")
        if host:
            init_db.PG_HOST = host
        if port:
            try:
                init_db.PG_PORT = int(port)
            except (TypeError, ValueError):
                pass
        if user:
            init_db.PG_USER = user
        if password:
            os.environ.setdefault("PGPASSWORD", password)
        if name:
            init_db.TARGET_DB_NAME = name

    # Initialize embedded PostgreSQL if not already done
    print(f"Debug: PG_DATA_DIR is {init_db.PG_DATA_DIR}")
    print(f"Debug: os.path.exists(PG_DATA_DIR) is {os.path.exists(init_db.PG_DATA_DIR)}")
    try:
        if using_sqlite or not using_postgres:
            print("SQLite mode requested; skipping embedded PostgreSQL bootstrap.")
        elif not os.path.exists(init_db.PG_DATA_DIR):
            print("Embedded PostgreSQL data directory not found. Initializing...")
            init_db.main()
            print("Embedded PostgreSQL initialization complete.")
        else:
            init_db.ensure_postgres_running()
    except Exception as exc:
        print(f"Warning: Failed to start embedded PostgreSQL automatically ({exc}).", file=sys.stderr)

    if not using_sqlite:
        _ensure_postgres_database()

    # If running the dev server without an explicit port, default to 8788 to avoid 8000 conflicts
    try:
        if len(sys.argv) >= 2 and sys.argv[1] == "runserver":
            # Find first positional (non-flag) arg after 'runserver'
            addr_arg = None
            for arg in sys.argv[2:]:
                if not arg.startswith("-"):
                    addr_arg = arg
                    break
            if addr_arg is None:
                host = os.environ.get("DJANGO_HOST", "0.0.0.0")
                port = os.environ.get("DJANGO_PORT", "8788")
                sys.argv.append(f"{host}:{port}")
    except Exception:
        # Don't block startup if any parsing error occurs
        pass
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

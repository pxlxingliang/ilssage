import re
import os
import sqlite3
from pathlib import Path
from typing import Literal, Dict, Any, Optional

from backend.mcp_server import mcp

DISALLOWED_KEYWORDS = [
    "INSERT",
    "REPLACE",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "ATTACH",
    "DETACH",
    "VACUUM",
    "REINDEX",
    "PRAGMA",
]

ALLOWED_LEADING_KEYWORDS = ["SELECT", "EXPLAIN", "WITH"]

_DISALLOWED_PATTERN = re.compile(
    r"\b(" + "|".join(DISALLOWED_KEYWORDS) + r")\b", re.IGNORECASE
)


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", "", sql)
    return sql


def _strip_string_literals(sql: str) -> str:
    sql = re.sub(r"'(?:[^']|'')*'", "''", sql)
    return sql


def _validate_sql(query: str) -> Optional[str]:
    cleaned = query.strip()
    if not cleaned:
        return "Query is empty"

    inspected = _strip_sql_comments(cleaned)
    inspected = _strip_string_literals(inspected)
    inspected = inspected.strip()

    if not inspected:
        return "Query contains only comments or strings"

    if ";" in inspected:
        return (
            "Multiple statements detected (semicolon found). "
            "Only single SELECT queries are allowed"
        )

    tokens = inspected.split()
    if not tokens:
        return "Query contains only comments or strings"

    first_word = tokens[0].upper()
    if first_word not in ALLOWED_LEADING_KEYWORDS:
        return (
            f"Disallowed leading keyword '{first_word}'. "
            "Only SELECT, EXPLAIN, and WITH (CTE) queries are permitted"
        )

    matches = _DISALLOWED_PATTERN.findall(inspected)
    if matches:
        unique = sorted(set(m.upper() for m in matches))
        return (
            f"Disallowed keyword(s) found: {', '.join(unique)}. "
            "Only read-only SELECT queries are permitted"
        )

    return None


def _open_db(db_path: str, db_type: str):
    if db_type != "sqlite3":
        return None, {
            "success": False,
            "error": (
                f"Unsupported database type '{db_type}'. "
                "Only 'sqlite3' is currently supported."
            ),
        }

    if not db_path:
        return None, {
            "success": False,
            "error": "Database path is empty. Please provide a valid path to the SQLite database file.",
        }

    if not Path(db_path).exists():
        return None, {
            "success": False,
            "error": f"Database file not found: {db_path}",
        }

    try:
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        return conn, None
    except sqlite3.Error as e:
        return None, {"success": False, "error": f"Failed to open database: {str(e)}"}


@mcp.tool()
def sqlite_query(
    db_path: str,
    db_type: Literal["sqlite3"],
    query: str,
) -> Dict[str, Any]:
    """
    Execute a read-only SQL query against a SQLite database.

    Only SELECT, EXPLAIN, and WITH (CTE) queries are permitted. Any statement that
    could modify the database (INSERT, UPDATE, DELETE, DROP, etc.) is rejected.

    Results are capped to avoid returning excessive data. If the result set exceeds
    the limit, the `truncated` flag is set to True and only the first N rows are returned.

    Args:
        db_path (str): Path to the SQLite database file.
        db_type (str): Type of database. Currently only "sqlite3" is supported.
        query (str): A read-only SQL query (SELECT / EXPLAIN / WITH ... SELECT).

    Returns:
        A dictionary with:
            - success (bool): Whether the query executed successfully.
            - error (str): Error description if success is False.
            - columns (list): Column names (only when success is True).
            - rows (list): List of rows, each row is a list of values (only when success is True).
            - row_count (int): Number of rows returned (only when success is True).
            - truncated (bool): Whether the result was truncated (only when success is True).
            - max_rows_allowed (int): The row limit applied (only when success is True).
    """
    err = _validate_sql(query)
    if err:
        return {"success": False, "error": err}

    max_rows_str = os.environ.get("ILSSAGE_SQLITE_MAX_ROWS", "10")
    try:
        max_rows = int(max_rows_str)
        if max_rows < 1:
            max_rows = 10
    except ValueError:
        max_rows = 10

    conn, err = _open_db(db_path, db_type)
    if err:
        return err

    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows

        if truncated:
            rows = rows[:max_rows]

        columns = (
            [desc[0] for desc in cursor.description]
            if cursor.description
            else []
        )
        data_rows = [list(row) for row in rows]
    except sqlite3.Error as e:
        return {"success": False, "error": f"SQLite error: {str(e)}"}
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return {
        "success": True,
        "columns": columns,
        "rows": data_rows,
        "row_count": len(data_rows),
        "truncated": truncated,
        "max_rows_allowed": max_rows,
    }


_TABLE_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


@mcp.tool()
def sqlite_list_tables(
    db_path: str,
    db_type: Literal["sqlite3"],
) -> Dict[str, Any]:
    """
    List all user tables in a SQLite database.

    Args:
        db_path (str): Path to the SQLite database file.
        db_type (str): Type of database. Currently only "sqlite3" is supported.

    Returns:
        A dictionary with:
            - success (bool): Whether the operation succeeded.
            - error (str): Error description if success is False.
            - tables (list): List of table names (only when success is True).
            - count (int): Number of tables found (only when success is True).
    """
    conn, err = _open_db(db_path, db_type)
    if err:
        return err

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        return {"success": False, "error": f"SQLite error: {str(e)}"}
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return {"success": True, "tables": tables, "count": len(tables)}


@mcp.tool()
def sqlite_list_columns(
    db_path: str,
    db_type: Literal["sqlite3"],
    table_name: str,
) -> Dict[str, Any]:
    """
    List column names and types for a specified table in a SQLite database.

    The table name is validated to only contain alphanumeric characters and
    underscores, and the table must exist in the database.

    Args:
        db_path (str): Path to the SQLite database file.
        db_type (str): Type of database. Currently only "sqlite3" is supported.
        table_name (str): Name of the table to inspect (e.g., 'molecules', 'features').

    Returns:
        A dictionary with:
            - success (bool): Whether the operation succeeded.
            - error (str): Error description if success is False.
            - table (str): The table name queried (only when success is True).
            - columns (list): List of dicts with "name" and "type" keys (only when success is True).
            - count (int): Number of columns found (only when success is True).
    """
    if not _TABLE_NAME_RE.match(table_name):
        return {
            "success": False,
            "error": (
                f"Invalid table name '{table_name}'. "
                "Table names must start with a letter or underscore "
                "and contain only alphanumeric characters and underscores."
            ),
        }

    conn, err = _open_db(db_path, db_type)
    if err:
        return err

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        if not cursor.fetchone():
            return {
                "success": False,
                "error": f"Table '{table_name}' not found in the database.",
            }

        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [
            {"name": row["name"], "type": row["type"] if row["type"] else ""}
            for row in cursor.fetchall()
        ]
    except sqlite3.Error as e:
        return {"success": False, "error": f"SQLite error: {str(e)}"}
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return {
        "success": True,
        "table": table_name,
        "columns": columns,
        "count": len(columns),
    }

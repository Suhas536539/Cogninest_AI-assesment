from __future__ import annotations

import re


FORBIDDEN_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "EXEC",
    "EXECUTE",
    "MERGE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "GRANT",
    "REVOKE",
    "SHUTDOWN",
    "VACUUM",
}

FORBIDDEN_PATTERNS = [
    re.compile(r"\bxp_\w+", re.IGNORECASE),
    re.compile(r"\bsp_\w+", re.IGNORECASE),
    re.compile(r"\bsqlite_master\b", re.IGNORECASE),
    re.compile(r"\bsqlite_schema\b", re.IGNORECASE),
    re.compile(r"\bsqlite_temp_master\b", re.IGNORECASE),
    re.compile(r"\bpragma_\w+", re.IGNORECASE),
]


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--.*?$", " ", sql, flags=re.MULTILINE)
    return sql


def validate_select_sql(sql: str) -> str:
    cleaned = _strip_sql_comments(sql or "").strip()
    if not cleaned:
        raise ValueError("Generated SQL is empty.")

    if cleaned.count(";") > 1 or (";" in cleaned[:-1]):
        raise ValueError("Only a single SQL statement is allowed.")

    normalized = re.sub(r"\s+", " ", cleaned).strip()
    upper_sql = normalized.upper()

    if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
        raise ValueError("Only SELECT queries are allowed.")

    tokens = set(re.findall(r"\b[A-Z_]+\b", upper_sql))
    forbidden = FORBIDDEN_KEYWORDS.intersection(tokens)
    if forbidden:
        blocked = ", ".join(sorted(forbidden))
        raise ValueError(f"Dangerous SQL keyword detected: {blocked}.")

    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(normalized):
            raise ValueError("System tables and dangerous SQL helpers are not allowed.")

    return normalized.rstrip(";")

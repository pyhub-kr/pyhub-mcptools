"""Session management for Python REPL with SQLite backend."""

import sqlite3
import pickle
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from contextlib import contextmanager
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages Python REPL sessions with SQLite persistence."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize session manager.

        Args:
            db_path: Path to SQLite database. Uses default if not provided.
        """
        if db_path is None:
            db_path = settings.APP_DATA_DIR / "python_sessions.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.executescript("""
                -- Sessions table
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_executions INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE
                );

                -- Session variables table
                CREATE TABLE IF NOT EXISTS session_variables (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    variable_name TEXT NOT NULL,
                    variable_type TEXT NOT NULL,
                    pickled_value BLOB NOT NULL,
                    size_bytes INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
                    UNIQUE(session_id, variable_name)
                );

                -- Execution history table
                CREATE TABLE IF NOT EXISTS execution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    code TEXT NOT NULL,
                    output TEXT,
                    error TEXT,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_sessions_last_accessed
                ON sessions(last_accessed);

                CREATE INDEX IF NOT EXISTS idx_variables_session
                ON session_variables(session_id);

                CREATE INDEX IF NOT EXISTS idx_history_session
                ON execution_history(session_id, executed_at);
            """)
            conn.commit()

    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new session.

        Args:
            session_id: Optional session ID. Auto-generated if not provided.

        Returns:
            The session ID.
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        with self._get_connection() as conn:
            try:
                conn.execute(
                    "INSERT INTO sessions (session_id) VALUES (?)",
                    (session_id,)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                # Session already exists, update last_accessed
                self._update_session_access(session_id)

        return session_id

    def _update_session_access(self, session_id: str):
        """Update session last accessed time and increment execution count."""
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE sessions
                   SET last_accessed = CURRENT_TIMESTAMP,
                       total_executions = total_executions + 1
                   WHERE session_id = ?""",
                (session_id,)
            )
            conn.commit()

    def save_variables(self, session_id: str, namespace: Dict[str, Any]):
        """Save session variables to database.

        Args:
            session_id: Session ID
            namespace: Dictionary of variables to save
        """
        # Filter out non-serializable and private variables
        variables_to_save = []

        for name, value in namespace.items():
            # Skip private variables and builtins
            if name.startswith('_') or name == '__builtins__':
                continue

            # Skip modules
            if hasattr(value, '__module__') and hasattr(value, '__name__'):
                continue

            try:
                # Try to pickle the value
                pickled = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
                size = len(pickled)

                # Skip if too large (10MB limit per variable)
                if size > 10 * 1024 * 1024:
                    logger.warning(f"Variable '{name}' too large ({size} bytes), skipping")
                    continue

                variables_to_save.append((
                    session_id,
                    name,
                    type(value).__name__,
                    pickled,
                    size
                ))
            except (pickle.PicklingError, TypeError) as e:
                logger.debug(f"Cannot pickle variable '{name}': {e}")
                continue

        # Save to database
        with self._get_connection() as conn:
            # Clear existing variables
            conn.execute("DELETE FROM session_variables WHERE session_id = ?", (session_id,))

            # Insert new variables
            conn.executemany(
                """INSERT OR REPLACE INTO session_variables
                   (session_id, variable_name, variable_type, pickled_value, size_bytes)
                   VALUES (?, ?, ?, ?, ?)""",
                variables_to_save
            )
            conn.commit()

        self._update_session_access(session_id)

    def load_variables(self, session_id: str) -> Dict[str, Any]:
        """Load session variables from database.

        Args:
            session_id: Session ID

        Returns:
            Dictionary of variables
        """
        namespace = {}

        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT variable_name, pickled_value
                   FROM session_variables
                   WHERE session_id = ?""",
                (session_id,)
            )

            for row in cursor:
                try:
                    value = pickle.loads(row['pickled_value'])
                    namespace[row['variable_name']] = value
                except (pickle.UnpicklingError, ImportError) as e:
                    logger.warning(f"Cannot unpickle variable '{row['variable_name']}': {e}")

        return namespace

    def list_sessions(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all sessions.

        Args:
            active_only: Only return active sessions

        Returns:
            List of session information
        """
        with self._get_connection() as conn:
            query = """
                SELECT
                    s.session_id,
                    s.created_at,
                    s.last_accessed,
                    s.total_executions,
                    s.is_active,
                    COUNT(DISTINCT v.variable_name) as variable_count,
                    COALESCE(SUM(v.size_bytes), 0) as total_size
                FROM sessions s
                LEFT JOIN session_variables v ON s.session_id = v.session_id
                WHERE 1=1
            """

            if active_only:
                query += " AND s.is_active = TRUE"

            query += " GROUP BY s.session_id ORDER BY s.last_accessed DESC"

            cursor = conn.execute(query)

            sessions = []
            for row in cursor:
                sessions.append({
                    'session_id': row['session_id'],
                    'created_at': row['created_at'],
                    'last_accessed': row['last_accessed'],
                    'total_executions': row['total_executions'],
                    'is_active': bool(row['is_active']),
                    'variable_count': row['variable_count'],
                    'total_size_bytes': row['total_size']
                })

        return sessions

    def get_session_variables(self, session_id: str) -> List[Dict[str, Any]]:
        """Get information about session variables.

        Args:
            session_id: Session ID

        Returns:
            List of variable information
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT variable_name, variable_type, size_bytes, updated_at
                   FROM session_variables
                   WHERE session_id = ?
                   ORDER BY variable_name""",
                (session_id,)
            )

            variables = []
            for row in cursor:
                variables.append({
                    'name': row['variable_name'],
                    'type': row['variable_type'],
                    'size_bytes': row['size_bytes'],
                    'updated_at': row['updated_at']
                })

        return variables

    def clear_session(self, session_id: str):
        """Clear all variables from a session.

        Args:
            session_id: Session ID
        """
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM session_variables WHERE session_id = ?",
                (session_id,)
            )
            conn.commit()

        self._update_session_access(session_id)

    def delete_session(self, session_id: str):
        """Delete a session completely.

        Args:
            session_id: Session ID
        """
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            conn.commit()

    def save_execution(self, session_id: str, code: str, output: str,
                      error: Optional[str], execution_time_ms: int):
        """Save execution history.

        Args:
            session_id: Session ID
            code: Executed code
            output: Output from execution
            error: Error message if any
            execution_time_ms: Execution time in milliseconds
        """
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO execution_history
                   (session_id, code, output, error, execution_time_ms)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, code, output, error, execution_time_ms)
            )
            conn.commit()

    def cleanup_old_sessions(self, days: int = 7):
        """Clean up old inactive sessions.

        Args:
            days: Number of days of inactivity before cleanup
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        with self._get_connection() as conn:
            conn.execute(
                """UPDATE sessions
                   SET is_active = FALSE
                   WHERE last_accessed < ? AND is_active = TRUE""",
                (cutoff_date.isoformat(),)
            )

            # Delete very old sessions (30 days)
            very_old_cutoff = datetime.now() - timedelta(days=30)
            conn.execute(
                "DELETE FROM sessions WHERE last_accessed < ?",
                (very_old_cutoff.isoformat(),)
            )

            conn.commit()

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed session information.

        Args:
            session_id: Session ID

        Returns:
            Session information or None if not found
        """
        sessions = self.list_sessions(active_only=False)
        for session in sessions:
            if session['session_id'] == session_id:
                return session
        return None
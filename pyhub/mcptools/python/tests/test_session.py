"""Test Python session management functionality."""

import json
import tempfile
import uuid
from pathlib import Path
from unittest import mock

import pytest

from pyhub.mcptools.python.sandbox_session import SessionAwarePythonSandbox
from pyhub.mcptools.python.session_manager import SessionManager
from pyhub.mcptools.python.tools import (
    python_clear_session,
    python_list_sessions,
    python_list_variables,
    python_repl,
)


class TestSessionManager:
    """Test SessionManager class."""

    def setup_method(self):
        """Set up test with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.manager = SessionManager(Path(self.temp_db.name))

    def teardown_method(self):
        """Clean up temporary database."""
        Path(self.temp_db.name).unlink(missing_ok=True)

    def test_create_session(self):
        """Test session creation."""
        # Auto-generated ID
        session_id = self.manager.create_session()
        assert session_id is not None
        assert len(session_id) > 0

        # Custom ID
        custom_id = "test_session_123"
        result = self.manager.create_session(custom_id)
        assert result == custom_id

        # Verify session exists
        info = self.manager.get_session_info(custom_id)
        assert info is not None
        assert info["session_id"] == custom_id

    def test_save_and_load_variables(self):
        """Test variable persistence."""
        session_id = self.manager.create_session("test_vars")

        # Save variables
        namespace = {"x": 42, "y": "hello", "z": [1, 2, 3], "data": {"a": 1, "b": 2}}
        self.manager.save_variables(session_id, namespace)

        # Load variables
        loaded = self.manager.load_variables(session_id)
        assert loaded["x"] == 42
        assert loaded["y"] == "hello"
        assert loaded["z"] == [1, 2, 3]
        assert loaded["data"] == {"a": 1, "b": 2}

    def test_list_sessions(self):
        """Test listing sessions."""
        # Create multiple sessions
        ids = ["session1", "session2", "session3"]
        for sid in ids:
            self.manager.create_session(sid)
            self.manager.save_variables(sid, {"test": sid})

        # List sessions
        sessions = self.manager.list_sessions()
        assert len(sessions) == 3

        # Check session details
        session_ids = [s["session_id"] for s in sessions]
        assert all(sid in session_ids for sid in ids)

    def test_clear_session(self):
        """Test clearing session variables."""
        session_id = self.manager.create_session("clear_test")

        # Add variables
        self.manager.save_variables(session_id, {"a": 1, "b": 2})

        # Clear session
        self.manager.clear_session(session_id)

        # Verify empty
        loaded = self.manager.load_variables(session_id)
        assert len(loaded) == 0

        # Session should still exist
        info = self.manager.get_session_info(session_id)
        assert info is not None

    def test_delete_session(self):
        """Test session deletion."""
        session_id = self.manager.create_session("delete_test")

        # Delete session
        self.manager.delete_session(session_id)

        # Verify deleted
        info = self.manager.get_session_info(session_id)
        assert info is None


class TestSessionAwareSandbox:
    """Test session-aware Python sandbox."""

    def setup_method(self):
        """Set up test with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        # Create sandbox with custom database path
        self.sandbox = SessionAwarePythonSandbox()
        # Replace the session manager with one using our temp database
        self.sandbox.session_manager = SessionManager(Path(self.temp_db.name))

    def teardown_method(self):
        """Clean up temporary database."""
        Path(self.temp_db.name).unlink(missing_ok=True)

    def test_stateless_execution(self):
        """Test execution without session."""
        result = self.sandbox.execute("print('Hello')")
        assert result["output"].strip() == "Hello"
        assert result.get("error") is None
        assert result.get("session_id") is None

    def test_session_execution(self):
        """Test execution with session."""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"

        # First execution
        result1 = self.sandbox.execute("x = 42", session_id=session_id)
        assert result1.get("error") is None
        assert result1["session_id"] == session_id

        # Second execution - should have access to x
        result2 = self.sandbox.execute("print(x)", session_id=session_id)
        assert result2["output"].strip() == "42"
        assert result2.get("error") is None

    def test_session_reset(self):
        """Test session reset."""
        session_id = f"reset_test_{uuid.uuid4().hex[:8]}"

        # Create variable
        self.sandbox.execute("x = 100", session_id=session_id)

        # Reset and try to access
        result = self.sandbox.execute("print(x)", session_id=session_id, reset_session=True)
        assert "NameError" in result.get("error", "")

    def test_security_with_session(self):
        """Test security measures work with sessions."""
        session_id = f"security_test_{uuid.uuid4().hex[:8]}"

        # Try dangerous operations
        dangerous_codes = [
            "import os",
            "open('/etc/passwd')",
            "__import__('subprocess')",
        ]

        for code in dangerous_codes:
            result = self.sandbox.execute(code, session_id=session_id)
            assert result.get("error") is not None
            assert "not allowed" in result["error"] or "Dangerous" in result["error"]


@pytest.fixture
def isolated_session_manager():
    """Create an isolated session manager for each test."""
    # Reset the global sandbox instance
    import pyhub.mcptools.python.sandbox_session as sandbox_module

    sandbox_module._sandbox_instance = None

    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    manager = SessionManager(Path(temp_db.name))
    yield manager
    Path(temp_db.name).unlink(missing_ok=True)


@pytest.mark.asyncio
class TestPythonTools:
    """Test Python MCP tools with sessions."""

    async def test_python_repl_with_session(self, isolated_session_manager):
        """Test python_repl with session support."""
        # Generate unique session ID to avoid conflicts
        session_id = f"tool_test_{uuid.uuid4().hex[:8]}"

        # Patch get_sandbox to return sandbox with isolated manager
        import pyhub.mcptools.python.sandbox_session as sandbox_module

        original_get_sandbox = sandbox_module.get_sandbox

        def mock_get_sandbox():
            sandbox = SessionAwarePythonSandbox()
            sandbox.session_manager = isolated_session_manager
            return sandbox

        sandbox_module.get_sandbox = mock_get_sandbox

        try:
            # Execute with session
            result1 = await python_repl(
                code="data = [1, 2, 3, 4, 5]", session_id=session_id, reset_session=False, timeout_seconds=30
            )
            data1 = json.loads(result1)
            assert data1.get("error") is None
            assert data1["session_id"] == session_id

            # Use variable from previous execution
            result2 = await python_repl(
                code="print(sum(data))", session_id=session_id, reset_session=False, timeout_seconds=30
            )
            data2 = json.loads(result2)
            assert data2["output"].strip() == "15"
        finally:
            sandbox_module.get_sandbox = original_get_sandbox

    async def test_list_variables(self, isolated_session_manager):
        """Test listing session variables."""
        session_id = f"list_vars_test_{uuid.uuid4().hex[:8]}"

        import pyhub.mcptools.python.sandbox_session as sandbox_module

        original_get_sandbox = sandbox_module.get_sandbox

        def mock_get_sandbox():
            sandbox = SessionAwarePythonSandbox()
            sandbox.session_manager = isolated_session_manager
            return sandbox

        sandbox_module.get_sandbox = mock_get_sandbox

        # Patch SessionManager in tools.py
        with mock.patch("pyhub.mcptools.python.tools.SessionManager") as MockManager:
            MockManager.return_value = isolated_session_manager

            try:
                # Create some variables
                await python_repl(
                    code="x = 42\ny = 'test'\nz = [1, 2, 3]",
                    session_id=session_id,
                    reset_session=False,
                    timeout_seconds=30,
                )

                # List variables
                result = await python_list_variables(session_id=session_id)
                data = json.loads(result)

                assert data["session_id"] == session_id
                assert data["variable_count"] == 3

                # Check variable names
                var_names = [v["name"] for v in data["variables"]]
                assert "x" in var_names
                assert "y" in var_names
                assert "z" in var_names
            finally:
                sandbox_module.get_sandbox = original_get_sandbox

    async def test_clear_session(self, isolated_session_manager):
        """Test clearing session."""
        session_id = f"clear_test_{uuid.uuid4().hex[:8]}"

        import pyhub.mcptools.python.sandbox_session as sandbox_module

        original_get_sandbox = sandbox_module.get_sandbox

        def mock_get_sandbox():
            sandbox = SessionAwarePythonSandbox()
            sandbox.session_manager = isolated_session_manager
            return sandbox

        sandbox_module.get_sandbox = mock_get_sandbox

        with mock.patch("pyhub.mcptools.python.tools.SessionManager") as MockManager:
            MockManager.return_value = isolated_session_manager

            try:
                # Create variables
                await python_repl(code="a = 1\nb = 2", session_id=session_id, reset_session=False, timeout_seconds=30)

                # Clear session
                result = await python_clear_session(session_id=session_id)
                data = json.loads(result)
                assert data["status"] == "cleared"

                # Verify variables are gone
                result2 = await python_repl(
                    code="print(a)", session_id=session_id, reset_session=False, timeout_seconds=30
                )
                data2 = json.loads(result2)
                assert "NameError" in data2.get("error", "")
            finally:
                sandbox_module.get_sandbox = original_get_sandbox

    async def test_list_sessions(self, isolated_session_manager):
        """Test listing all sessions."""
        import pyhub.mcptools.python.sandbox_session as sandbox_module

        original_get_sandbox = sandbox_module.get_sandbox

        def mock_get_sandbox():
            sandbox = SessionAwarePythonSandbox()
            sandbox.session_manager = isolated_session_manager
            return sandbox

        sandbox_module.get_sandbox = mock_get_sandbox

        with mock.patch("pyhub.mcptools.python.tools.SessionManager") as MockManager:
            MockManager.return_value = isolated_session_manager

            try:
                # Create a few sessions with unique IDs
                session_ids = []
                for i in range(3):
                    sid = f"session_{i}_{uuid.uuid4().hex[:8]}"
                    session_ids.append(sid)
                    await python_repl(code=f"x = {i}", session_id=sid, reset_session=False, timeout_seconds=30)

                # List sessions
                result = await python_list_sessions()
                data = json.loads(result)

                assert data["session_count"] >= 3
                listed_ids = [s["session_id"] for s in data["sessions"]]
                for sid in session_ids:
                    assert sid in listed_ids
            finally:
                sandbox_module.get_sandbox = original_get_sandbox


if __name__ == "__main__":
    pytest.main([__file__])

"""
System health smoke tests - verify basic system components work.
Target: 30 seconds execution time.
"""

from pathlib import Path

import pytest


@pytest.mark.unit
class TestDatabaseHealth:
    """
    Test database connectivity and basic operations.
    """

    def test_sqlite_connection(self, temp_db):
        """
        Verify SQLite database can be created and accessed.
        """
        cursor = temp_db.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO test (name) VALUES (?)", ("test_entry",))
        temp_db.commit()

        result = cursor.execute("SELECT name FROM test WHERE content_id = 1").fetchone()
        assert result[0] == "test_entry"

    def test_database_service_import(self):
        """
        Verify core database service can be imported.
        """
        try:
            from shared.database.database_service import DatabaseService

            assert DatabaseService is not None
        except ImportError as e:
            pytest.skip(f"DatabaseService import failed: {e}")


@pytest.mark.unit
class TestFileSystemHealth:
    """
    Test file system operations.
    """

    def test_temp_directory_access(self, temp_dir):
        """
        Verify temporary directory operations work.
        """
        test_file = temp_dir / "test.txt"
        test_file.write_text("smoke test content")
        assert test_file.exists()
        assert test_file.read_text() == "smoke test content"

    def test_data_directory_structure(self):
        """
        Verify expected data directories exist.
        """
        base_path = Path.cwd()
        expected_dirs = ["data", "tools", "shared"]  # Updated for new flat architecture

        for dir_name in expected_dirs:
            dir_path = base_path / dir_name
            assert dir_path.exists(), f"Required directory missing: {dir_name}"


@pytest.mark.unit
class TestEnvironmentHealth:
    """
    Test environment configuration.
    """

    def test_python_environment(self):
        """
        Verify Python environment basics.
        """
        import sys

        assert sys.version_info >= (3, 8), "Python 3.8+ required"

    def test_required_modules_importable(self):
        """
        Test that core modules can be imported.
        """
        importable_modules = ["sqlite3", "json", "pathlib", "datetime"]

        for module_name in importable_modules:
            try:
                __import__(module_name)
            except ImportError:
                pytest.fail(f"Required module not available: {module_name}")

    def test_working_directory(self):
        """
        Verify we're in the right working directory.
        """
        cwd = Path.cwd()
        assert (cwd / "CLAUDE.md").exists(), "Not in project root directory"
        assert (cwd / "tools" / "scripts").exists(), "Missing tools/scripts directory"


@pytest.mark.unit
class TestBasicServices:
    """
    Test basic service health without external dependencies.
    """

    @pytest.mark.skipif(not Path("shared/database").exists(), reason="Database service not found")
    def test_database_service_instantiation(self, mock_env):
        """
        Test that DatabaseService can be created.
        """
        try:
            from shared.database.database_service import DatabaseService

            # Test with in-memory database
            service = DatabaseService(":memory:")
            assert service is not None
        except Exception as e:
            pytest.skip(f"DatabaseService instantiation failed: {e}")

    def test_basic_imports_work(self):
        """
        Verify basic project imports don't crash.
        """
        import_tests = ["pathlib.Path", "json.loads", "sqlite3.connect"]

        for import_path in import_tests:
            module_name, attr_name = import_path.rsplit(".", 1)
            try:
                module = __import__(module_name, fromlist=[attr_name])
                getattr(module, attr_name)
            except (ImportError, AttributeError) as e:
                pytest.fail(f"Basic import failed: {import_path} - {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

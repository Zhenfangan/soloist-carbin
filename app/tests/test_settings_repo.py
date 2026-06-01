"""SettingsRepo 数据访问层测试"""

from __future__ import annotations

from app.repositories.settings_repo import SettingsRepo


class TestSettingsRepo:
    def test_set_and_get(self, temp_db: str) -> None:
        repo = SettingsRepo(temp_db)
        repo.set("test_key", "hello")
        assert repo.get("test_key") == "hello"

    def test_get_nonexistent_returns_none(self, temp_db: str) -> None:
        repo = SettingsRepo(temp_db)
        assert repo.get("no_such_key") is None

    def test_set_overwrites(self, temp_db: str) -> None:
        repo = SettingsRepo(temp_db)
        repo.set("key", "v1")
        repo.set("key", "v2")
        assert repo.get("key") == "v2"

    def test_get_all_empty(self, temp_db: str) -> None:
        repo = SettingsRepo(temp_db)
        assert repo.get_all() == {}

    def test_get_all_returns_all(self, temp_db: str) -> None:
        repo = SettingsRepo(temp_db)
        repo.set("a", "1")
        repo.set("b", "2")
        result = repo.get_all()
        assert result == {"a": "1", "b": "2"}

    def test_batch_set(self, temp_db: str) -> None:
        repo = SettingsRepo(temp_db)
        repo.batch_set({"x": "10", "y": "20"})
        assert repo.get("x") == "10"
        assert repo.get("y") == "20"

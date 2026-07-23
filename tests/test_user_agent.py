import pytest

from app.network.user_agent import UserAgentManager


def test_next_cycles_through_the_pool() -> None:
    manager = UserAgentManager(["a", "b", "c"])
    assert [manager.next() for _ in range(6)] == ["a", "b", "c", "a", "b", "c"]


def test_random_returns_a_pool_member() -> None:
    manager = UserAgentManager(["a", "b", "c"])
    for _ in range(10):
        assert manager.random() in {"a", "b", "c"}


def test_register_extends_pool_without_duplicates() -> None:
    manager = UserAgentManager(["a", "b"])
    manager.register(["b", "c"])
    assert manager.pool_size == 3


def test_defaults_to_builtin_user_agents_when_none_given() -> None:
    manager = UserAgentManager()
    assert manager.pool_size > 0


def test_rejects_empty_pool() -> None:
    with pytest.raises(ValueError):
        UserAgentManager([])

from app.config.settings import get_settings


def test_settings_is_cached_singleton() -> None:
    assert get_settings() is get_settings()


def test_default_values_are_sane() -> None:
    settings = get_settings()
    assert settings.MAX_CONCURRENCY >= 1
    assert settings.REQUEST_TIMEOUT_SECONDS > 0
    assert settings.APP_NAME

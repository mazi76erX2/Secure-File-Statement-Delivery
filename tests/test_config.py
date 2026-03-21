from config import Settings


def test_database_url_sync_appends_sslmode_when_required() -> None:
    settings = Settings(
        database_username="user",
        database_password="pass",
        database_host="db.internal",
        database_port=5432,
        database_name="appdb",
        database_ssl_mode="require",
    )

    assert settings.database_url_sync.endswith("?sslmode=require")


def test_database_connect_args_async_sets_ssl_when_required() -> None:
    settings = Settings(database_ssl_mode="require")

    assert settings.database_connect_args_async == {"ssl": True}


def test_redis_url_uses_rediss_and_password_query() -> None:
    settings = Settings(
        cache_host="cache.internal",
        cache_port=6380,
        cache_db=0,
        cache_password="redis-secret",
        cache_use_ssl=True,
        cache_ssl_cert_reqs="required",
    )

    assert settings.redis_url == (
        "rediss://:redis-secret@cache.internal:6380/0?ssl_cert_reqs=required"
    )


def test_redis_url_encodes_special_characters_in_credentials() -> None:
    settings = Settings(
        cache_host="cache.internal",
        cache_port=6379,
        cache_db=1,
        cache_username="user@name",
        cache_password="p@ss:/word",
    )

    assert (
        settings.redis_url
        == "redis://user%40name:p%40ss%3A%2Fword@cache.internal:6379/1"
    )

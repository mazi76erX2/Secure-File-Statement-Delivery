from api.statements import _build_content_disposition, _build_download_rate_limit_key


def test_content_disposition_sanitizes_filename() -> None:
    header = _build_content_disposition('..//sec\\ret"name.pdf\r\n')

    assert ".." not in header
    assert '\\"' not in header
    assert "\r" not in header
    assert "\n" not in header
    assert "filename*=UTF-8''" in header
    assert "attachment;" in header
    assert "sec" in header


def test_download_rate_limit_key_shape() -> None:
    key = _build_download_rate_limit_key("127.0.0.1")
    assert key == "statement-download-rate:127.0.0.1"

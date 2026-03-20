from utils.sa_id import validate_sa_id


def test_validate_sa_id_accepts_known_valid_id() -> None:
    assert validate_sa_id("8001015009087")


def test_validate_sa_id_rejects_bad_checksum() -> None:
    assert not validate_sa_id("8001015009088")


def test_validate_sa_id_rejects_invalid_month_and_day() -> None:
    assert not validate_sa_id("9013325009087")

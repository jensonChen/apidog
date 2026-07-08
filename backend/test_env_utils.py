import pytest

from env_utils import normalize_url


def test_normalize_url_adds_http():
    assert normalize_url("localhost:9019/starter") == "http://localhost:9019/starter"
    assert normalize_url("127.0.0.1:9019") == "http://127.0.0.1:9019"


def test_normalize_url_keeps_existing_protocol():
    assert normalize_url("http://127.0.0.1:9019") == "http://127.0.0.1:9019"
    assert normalize_url("https://api.example.com") == "https://api.example.com"

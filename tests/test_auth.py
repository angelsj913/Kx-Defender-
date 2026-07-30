import pytest

from kx_defender.auth import AuthorizationError, validate_params


def test_simulate_requires_scope():
    with pytest.raises(AuthorizationError):
        validate_params({"mode": "simulate"})


def test_simulate_ok_with_lab_scope():
    cleaned = validate_params({"authorized_scope": "lab", "mode": "simulate", "domain": "lab.local"})
    assert cleaned["mode"] == "simulate"


def test_execute_blocks_public_host():
    with pytest.raises(AuthorizationError):
        validate_params(
            {
                "authorized_scope": "owned",
                "mode": "execute",
                "url": "https://example.com/",
            }
        )


def test_execute_allows_localhost():
    cleaned = validate_params(
        {
            "authorized_scope": "owned",
            "mode": "execute",
            "url": "http://127.0.0.1:8080/",
        }
    )
    assert cleaned["mode"] == "execute"

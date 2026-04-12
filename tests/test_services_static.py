from aac_backend.services.artefact_service import fingerprint


def test_fingerprint_is_stable_for_key_order() -> None:
    assert fingerprint({"b": 2, "a": 1}) == fingerprint({"a": 1, "b": 2})

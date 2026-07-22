import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def test_web_uses_modular_es_module_entrypoint() -> None:
    index = (WEB / "index.html").read_text()

    assert re.search(
        r'<script type="module" src="\./js/app\.js(?:\?[^"]+)?"></script>',
        index,
    )
    assert "<script>" not in index
    assert (WEB / "styles" / "app.css").exists()
    assert (WEB / "js" / "api" / "client.js").exists()


def test_feature_modules_do_not_call_transport_directly() -> None:
    feature_files = sorted((WEB / "js" / "features").glob("*.js"))

    assert feature_files
    for path in feature_files:
        source = path.read_text()
        assert "fetch(" not in source, f"{path.name} bypasses the shared API client"
        assert "Authorization" not in source, f"{path.name} handles authentication directly"


def test_browser_token_is_session_scoped() -> None:
    state_source = (WEB / "js" / "state.js").read_text()

    assert 'sessionStorage.getItem("aac_token")' in state_source
    assert 'localStorage.getItem("aac_token")' not in state_source

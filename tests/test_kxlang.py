import pytest

from kx_defender.kx_cli import main as kx_main
from kx_defender.kxlang import KxLangError, list_verbs, parse_argv, parse_line
from kx_defender.orchestrator import Orchestrator


def test_lexicon_has_core_verbs():
    verbs = list_verbs()
    for v in ["sentry", "roast", "relay", "loot", "bait", "breach", "crack", "nexus", "probe", "sweep", "forge"]:
        assert v in verbs


def test_parse_defaults_scope_to_lab():
    cmd = parse_argv(["roast", "tickets", "--sim"])
    assert cmd.params["authorized_scope"] == "lab"
    assert cmd.params["mode"] == "simulate"


def test_parse_sentry_without_flags():
    cmd = parse_argv(["sentry"])
    assert cmd.verb == "sentry"
    assert cmd.params["authorized_scope"] == "lab"
    assert cmd.params["mode"] == "simulate"


def test_parse_roast_and_run():
    cmd = parse_line("roast tickets --scope lab --realm lab.local --sim")
    assert cmd.verb == "roast"
    assert cmd.module == "performing-kerberoasting-attack"
    assert cmd.params["authorized_scope"] == "lab"
    assert cmd.params["mode"] == "simulate"
    result = Orchestrator().run(cmd.module, cmd.params)
    assert result.status == "ok"


def test_parse_pact_maps_to_engagement():
    cmd = parse_argv(["sentry", "detect", "--scope", "pact", "--sim"])
    assert cmd.params["authorized_scope"] == "engagement"


def test_parse_nexus_bind():
    cmd = parse_line("nexus listen --scope lab --live --bind 127.0.0.1:4455")
    assert cmd.params["mode"] == "execute"
    assert cmd.params["host"] == "127.0.0.1"
    assert cmd.params["port"] == 4455
    assert cmd.params["action"] == "start_listener"


def test_parse_sweep_web():
    cmd = parse_line("sweep web --scope owned --url http://127.0.0.1/ --sim")
    assert cmd.module == "web_scanner"
    assert cmd.params["url"] == "http://127.0.0.1/"


def test_unknown_verb():
    with pytest.raises(KxLangError):
        parse_argv(["nukem", "all", "--scope", "lab"])


def test_kx_cli_lexicon(capsys):
    kx_main(["lexicon"])
    out = capsys.readouterr().out
    assert "DEFCOM" in out
    assert "sentry" in out


def test_kx_slash_h_help(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("KX_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("KX_LANG", "en")
    with pytest.raises(SystemExit) as exc:
        kx_main(["/h"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "KxLang / DEFCOM" in out
    assert "kx /h" in out
    assert "roast" in out
    assert "--scope" in out


def test_kx_slash_h_verb_help(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("KX_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("KX_LANG", "en")
    with pytest.raises(SystemExit) as exc:
        kx_main(["/h", "roast"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "KxLang verb: roast" in out
    assert "performing-kerberoasting-attack" in out


def test_kx_verb_slash_h(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("KX_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("KX_LANG", "en")
    with pytest.raises(SystemExit) as exc:
        kx_main(["nexus", "/h"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "KxLang verb: nexus" in out


def test_kx_help_unknown_verb(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("KX_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("KX_LANG", "en")
    with pytest.raises(SystemExit) as exc:
        kx_main(["/h", "nukem"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "unknown verb" in err


def test_lang_get_set(capsys, tmp_path, monkeypatch):
    from kx_defender import i18n

    cfg = tmp_path / "config.json"
    monkeypatch.setenv("KX_CONFIG", str(cfg))
    monkeypatch.delenv("KX_LANG", raising=False)

    with pytest.raises(SystemExit) as exc:
        kx_main(["lang"])
    assert exc.value.code == 0
    assert "language: en" in capsys.readouterr().out

    with pytest.raises(SystemExit) as exc:
        kx_main(["lang", "ko"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "ko" in out
    assert i18n.get_lang() == "ko"

    with pytest.raises(SystemExit) as exc:
        kx_main(["/h"])
    assert exc.value.code == 0
    help_out = capsys.readouterr().out
    assert "사용법:" in help_out
    assert "kx lang" in help_out
    assert "Usage:" not in help_out

    with pytest.raises(SystemExit) as exc:
        kx_main(["lang", "en"])
    assert exc.value.code == 0
    assert i18n.get_lang() == "en"

    with pytest.raises(SystemExit) as exc:
        kx_main(["/h"])
    assert exc.value.code == 0
    help_en = capsys.readouterr().out
    assert "Usage:" in help_en
    assert "사용법:" not in help_en


def test_update_is_meta_not_verb(monkeypatch):
    calls = []

    def fake_run(cmd, check=False):
        calls.append(cmd)

        class R:
            returncode = 0

        return R()

    monkeypatch.setattr("kx_defender.kx_cli.subprocess.run", fake_run)
    monkeypatch.setattr(
        "kx_defender.kx_cli._find_update_js",
        lambda: __import__("pathlib").Path("/tmp/fake-kx-update.js"),
    )
    with pytest.raises(SystemExit) as exc:
        kx_main(["update"])
    assert exc.value.code == 0
    assert calls and "fake-kx-update.js" in str(calls[0][-1])


def test_upgrade_alias(monkeypatch):
    monkeypatch.setattr(
        "kx_defender.kx_cli._run_update",
        lambda: 0,
    )
    with pytest.raises(SystemExit) as exc:
        kx_main(["upgrade"])
    assert exc.value.code == 0


def test_lang_rejects_unknown(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("KX_CONFIG", str(tmp_path / "config.json"))
    with pytest.raises(SystemExit) as exc:
        kx_main(["lang", "fr"])
    assert exc.value.code == 2

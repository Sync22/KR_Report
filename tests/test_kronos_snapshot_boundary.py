import importlib.util
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture
def lab(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "path", sys.path.copy())
    # Optional forecast packages are not needed to exercise the real SQLite boundary.
    for name in ("pandas", "torch", "model"):
        module = ModuleType(name)
        if name == "model":
            module.Kronos = object
            module.KronosPredictor = object
            module.KronosTokenizer = object
        monkeypatch.setitem(sys.modules, name, module)
    script = Path(__file__).resolve().parents[1] / "scripts/experimental/kronos_backtest_experiment.py"
    spec = importlib.util.spec_from_file_location("kronos_snapshot_boundary", script)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "__file__", str(tmp_path / "project/scripts/experimental/kronos_backtest_experiment.py"))
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    return module


def test_kronos_missing_snapshot_does_not_create_a_database(tmp_path, lab) -> None:
    source = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        lab._connect(source)
    assert not source.exists()


def test_kronos_snapshot_connection_can_read_but_cannot_write(tmp_path, lab) -> None:
    source = tmp_path / "snapshot with spaces.db"
    with closing(sqlite3.connect(source)) as connection:
        connection.execute("CREATE TABLE evidence (value TEXT)")
        connection.execute("INSERT INTO evidence VALUES ('saved')")
        connection.commit()
    before = source.read_bytes()
    with closing(lab._connect(source)) as connection:
        assert connection.execute("SELECT value FROM evidence").fetchone()["value"] == "saved"
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("INSERT INTO evidence VALUES ('unexpected')")
        connection.execute("PRAGMA query_only = OFF")
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("INSERT INTO evidence VALUES ('still unexpected')")
    assert source.read_bytes() == before


def test_kronos_requires_an_explicit_snapshot_path(monkeypatch, lab) -> None:
    monkeypatch.setattr(sys, "argv", ["kronos", "--from-date", "2026-04-01", "--to-date", "2026-04-30"])
    with pytest.raises(SystemExit) as error:
        lab.main()
    assert error.value.code == 2


@pytest.mark.parametrize("configuration", ["default", "environment", "dotenv"])
def test_kronos_rejects_the_operating_database(tmp_path, monkeypatch, lab, configuration) -> None:
    project_root = Path(lab.__file__).parents[2]
    operating = project_root / ("data/stock_monitor.db" if configuration == "default" else "custom.db")
    operating.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(operating)) as connection:
        connection.execute("CREATE TABLE evidence (value TEXT)")
    if configuration == "environment":
        monkeypatch.setenv("STOCK_MONITOR_DB_PATH", str(operating))
    if configuration == "dotenv":
        (project_root / ".env").write_text("STOCK_MONITOR_DB_PATH=custom.db\n", encoding="utf-8")
    with pytest.raises(ValueError, match="operating database"):
        lab._connect(operating)
    with pytest.raises(ValueError, match="operating database"):
        lab.run_experiment(SimpleNamespace(db_path=str(operating)))


def test_kronos_rejects_a_hardlink_to_the_operating_database(tmp_path, lab) -> None:
    operating = Path(lab.__file__).parents[2] / "data/stock_monitor.db"
    operating.parent.mkdir(parents=True)
    with closing(sqlite3.connect(operating)) as connection:
        connection.execute("CREATE TABLE evidence (value TEXT)")
    alias = tmp_path / "snapshot.db"
    os.link(operating, alias)
    with pytest.raises(ValueError, match="operating database"):
        lab._connect(alias)


def test_kronos_protects_configured_relative_path_from_other_working_directory(tmp_path, monkeypatch, lab) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STOCK_MONITOR_DB_PATH", "custom.db")
    operating = tmp_path / "custom.db"
    with closing(sqlite3.connect(operating)) as connection:
        connection.execute("CREATE TABLE evidence (value TEXT)")
    with pytest.raises(ValueError, match="operating database"):
        lab._connect(operating)

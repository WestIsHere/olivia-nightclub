"""Consistent SQLite snapshots and offline recovery; never overwrite a database."""

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile


REQUIRED_TABLES = {
    "users", "sessions", "clubs", "service_log", "transactions", "notifications",
    "trades", "city_feed", "settings", "audio_assets", "active_showcases", "robberies",
}


def inspect_connection(connection):
    if [row[0] for row in connection.execute("PRAGMA integrity_check")] != ["ok"]:
        raise ValueError("Sauvegarde SQLite endommagée.")
    tables = {row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if not REQUIRED_TABLES <= tables:
        raise ValueError("Base incomplète : tables du jeu manquantes.")
    if connection.execute(
        "SELECT COUNT(*) FROM clubs c LEFT JOIN users u ON u.id=c.user_id WHERE u.id IS NULL"
    ).fetchone()[0]:
        raise ValueError("Base incohérente : club sans compte propriétaire.")
    for row in connection.execute("SELECT state FROM clubs"):
        if not isinstance(json.loads(row[0]), dict):
            raise ValueError("État de club invalide.")
    return {
        "integrity": "ok",
        "rows": {table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                 for table in sorted(REQUIRED_TABLES)},
        "last_club_update": connection.execute("SELECT MAX(updated_at) FROM clubs").fetchone()[0],
    }


@contextlib.contextmanager
def readonly(path):
    source = Path(path).resolve(strict=True)
    connection = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=15)
    try:
        connection.execute("PRAGMA query_only=ON")
        yield connection
    finally:
        connection.close()


def inspect_database(path):
    with readonly(path) as connection:
        connection.execute("BEGIN")
        return inspect_connection(connection)


def snapshot(connection, destination):
    """Include committed WAL data. The caller locks a shared game connection."""
    target = Path(destination).resolve()
    if any(Path(str(target) + suffix).exists() for suffix in ("", "-wal", "-shm")):
        raise FileExistsError("La destination existe déjà ; aucun fichier n'a été remplacé.")
    if connection.in_transaction:
        raise RuntimeError("Terminez la transaction avant de créer une sauvegarde.")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".olivia-snapshot-", dir=target.parent)
    os.close(fd)
    temporary = Path(temporary)
    try:
        with contextlib.closing(sqlite3.connect(temporary)) as output:
            connection.backup(output)
            output.execute("PRAGMA journal_mode=DELETE")
            report = inspect_connection(output)
        with temporary.open("rb") as stream:
            report["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        with temporary.open("rb+") as stream:
            os.fsync(stream.fileno())
        # Same filesystem: atomic publication refusing even a racing target file.
        os.link(temporary, target)
        return report
    finally:
        temporary.unlink(missing_ok=True)


def restore(source, destination):
    with readonly(source) as connection:
        return snapshot(connection, destination)


def require_existing_database(path):
    required = os.environ.get("OLIVIA_REQUIRE_EXISTING_DB")
    if required is None:
        required = "1" if os.environ.get("RENDER", "").lower() == "true" else "0"
    if required.lower() not in {"0", "false", "no", "off"}:
        try:
            inspect_database(path)
        except (OSError, ValueError, sqlite3.Error) as exc:
            raise RuntimeError(
                "Démarrage bloqué : base existante absente ou invalide. "
                "Restaurer une sauvegarde complète vers OLIVIA_DB avant de démarrer ; "
                "aucune base vide n'a été créée. Voir docs/SAUVEGARDE.md."
            ) from exc


def main():
    parser = argparse.ArgumentParser(description="Sauvegarde et restauration sûre d'OLIVIA")
    commands = parser.add_subparsers(dest="operation", required=True)
    check = commands.add_parser("inspect")
    check.add_argument("source")
    for name in ("backup", "restore"):
        command = commands.add_parser(name)
        command.add_argument("source")
        command.add_argument("destination", help="Nouveau fichier, jamais un fichier existant")
    args = parser.parse_args()
    try:
        report = inspect_database(args.source) if args.operation == "inspect" else restore(args.source, args.destination)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        parser.exit(1, f"Échec : {exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

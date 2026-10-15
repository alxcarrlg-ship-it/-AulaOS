"""Versioned core-schema upgrades, with a verified pre-upgrade backup."""
import datetime as dt
from pathlib import Path
import sqlite3
import uuid

CURRENT_VERSION=1

def prepare(con,db_path):
    version=con.execute('PRAGMA user_version').fetchone()[0]
    if version>CURRENT_VERSION:raise ValueError('Esta base fue actualizada por una versión más reciente de AulaOS. Usa esa versión; no se modificó la base.')
    existing=con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    if version==CURRENT_VERSION or not existing:return None
    if con.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('La base necesita revisión de integridad antes de actualizar; no se migró.')
    folder=Path(db_path).parent/'migration_backups';folder.mkdir(exist_ok=True)
    target=folder/f'before_v{version}_to_v{CURRENT_VERSION}_{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}_{uuid.uuid4().hex[:8]}.sqlite3'
    backup=sqlite3.connect(target)
    try:
        con.backup(backup)
        if backup.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('No se pudo verificar el respaldo previo; no se migró.')
    finally:backup.close()
    return target

def upgrade(con):
    con.execute('BEGIN IMMEDIATE')
    try:
        version=con.execute('PRAGMA user_version').fetchone()[0]
        if version>CURRENT_VERSION:raise ValueError('Base de una versión más reciente.')
        if version<1:
            columns={r[1] for r in con.execute('PRAGMA table_info(students)')}
            if 'external_id' not in columns:con.execute('ALTER TABLE students ADD COLUMN external_id TEXT')
            con.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_student_external_id ON students(group_id,external_id) WHERE external_id IS NOT NULL')
            con.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at TEXT NOT NULL)')
            con.execute('INSERT INTO schema_migrations VALUES(1,?,?)',('Matrícula por grupo; base de migraciones explícitas',dt.datetime.now().astimezone().isoformat()))
            con.execute('PRAGMA user_version=1')
        con.commit()
    except Exception:con.rollback();raise

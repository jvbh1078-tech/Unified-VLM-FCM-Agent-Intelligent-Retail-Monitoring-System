from __future__ import annotations
from pathlib import Path
from zipfile import ZipFile, BadZipFile

class UnsafeZipError(Exception):
    pass

def safe_extract(zip_path: str | Path, dest_dir: str | Path, *, max_files: int = 3000, max_uncompressed_mb: int = 500) -> None:
    zip_path=Path(zip_path); dest_dir=Path(dest_dir).resolve(); dest_dir.mkdir(parents=True, exist_ok=True)
    total=0; max_bytes=max_uncompressed_mb*1024*1024
    try:
        with ZipFile(zip_path) as zf:
            infos=zf.infolist()
            if len(infos)>max_files:
                raise UnsafeZipError(f"too many files: {len(infos)}")
            for info in infos:
                total += info.file_size
                if total>max_bytes:
                    raise UnsafeZipError("uncompressed size too large")
                target=(dest_dir/info.filename).resolve()
                if not str(target).startswith(str(dest_dir)):
                    raise UnsafeZipError(f"zip path traversal blocked: {info.filename}")
            zf.extractall(dest_dir)
    except BadZipFile as e:
        raise UnsafeZipError(f"bad zip file: {e}") from e

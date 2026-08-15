"""Create an AgentCore ZIP with Linux file modes from a staged directory."""

import argparse
import stat
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

_OTEL_LAUNCHER = """#!/usr/bin/env python3
import sys

from opentelemetry.instrumentation.auto_instrumentation import run

if __name__ == "__main__":
    sys.exit(run())
"""


def _write_bytes(
    archive: ZipFile,
    archive_name: str,
    content: bytes,
    *,
    mode: int,
) -> None:
    info = ZipInfo(archive_name)
    info.create_system = 3
    info.compress_type = ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | mode) << 16
    archive.writestr(info, content)


def create_archive(staging_path: Path, output_path: Path) -> None:
    """Archive staged files and synthesize a portable OTEL console script."""
    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as archive:
        for source in sorted(staging_path.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(staging_path).as_posix()
            # Cross-platform pip creates Windows console launchers even when it
            # downloads Linux wheels. They are not usable in AgentCore Linux.
            if relative.startswith("bin/") and source.suffix.casefold() == ".exe":
                continue
            _write_bytes(archive, relative, source.read_bytes(), mode=0o644)

        launcher = _OTEL_LAUNCHER.encode("utf-8")
        _write_bytes(
            archive,
            "opentelemetry-instrument",
            launcher,
            mode=0o755,
        )
        _write_bytes(
            archive,
            "bin/opentelemetry-instrument",
            launcher,
            mode=0o755,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("staging_path", type=Path)
    parser.add_argument("output_path", type=Path)
    args = parser.parse_args()
    create_archive(args.staging_path, args.output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

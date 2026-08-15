"""Project-wide pytest configuration."""

import ctypes
import re

import pytest


def _windows_security_identity() -> str:
    """Return a filesystem-safe name for the active Windows security token."""
    buffer = ctypes.create_unicode_buffer(256)
    size = ctypes.c_ulong(len(buffer))
    if not ctypes.windll.advapi32.GetUserNameW(buffer, ctypes.byref(size)):
        raise ctypes.WinError()
    return re.sub(r"[^A-Za-z0-9_.-]", "_", buffer.value)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Keep temp files separate for interactive and sandbox Windows users."""
    if config.option.basetemp is None:
        identity = _windows_security_identity()
        config.option.basetemp = str(config.rootpath / f".pytest-tmp-{identity}")

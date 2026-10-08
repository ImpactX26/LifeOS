import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PORTS = (8101, 8102, 8103, 8104)


def _open(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture(scope="session")
def mcp_servers():
    """Real MCP servers over HTTP, forced to seeded data. If run_servers.py is already up, those answer instead."""
    env = {**os.environ, "LIFEOS_OFFLINE": "1"}
    procs = [subprocess.Popen([sys.executable, str(p)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
             for p in sorted((ROOT / "mcp_servers").glob("*_server.py"))]
    deadline = time.time() + 20
    while not all(_open(p) for p in PORTS):
        assert time.time() < deadline, "MCP servers did not start"
        time.sleep(0.2)
    yield
    for p in procs:
        p.terminate()

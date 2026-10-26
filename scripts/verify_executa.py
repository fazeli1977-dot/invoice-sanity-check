"""Check the actual release executable, including a persistent stdio session.

Usage: python scripts/verify_executa.py path/to/executable [--version 0.3.0]
"""

import argparse
import json
from pathlib import Path
from queue import Empty, Queue
import subprocess
import tarfile
import tempfile
from threading import Thread
import time


def verify(executable, version):
    executable = Path(executable).resolve(strict=True)
    process = subprocess.Popen(
        [str(executable)], cwd=executable.parent, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
        bufsize=1,
    )
    replies = Queue()
    errors = []

    def read_stdout():
        for line in process.stdout:
            replies.put(line)
        replies.put(None)

    def read_stderr():
        errors.extend(process.stderr.readlines())

    Thread(target=read_stdout, daemon=True).start()
    Thread(target=read_stderr, daemon=True).start()

    def rpc(method, request_id, params=None):
        request = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            request["params"] = params
        start = time.monotonic()
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()
        try:
            line = replies.get(timeout=15)
        except Empty:
            raise AssertionError(f"{method}: response timed out") from None
        assert line is not None, f"{method}: executable stopped: {''.join(errors)}"
        reply = json.loads(line)
        assert reply.get("jsonrpc") == "2.0" and reply.get("id") == request_id, reply
        assert ("result" in reply) != ("error" in reply), reply
        print(f"{method}: {time.monotonic() - start:.3f}s")
        return reply

    try:
        initialized = rpc("initialize", 0)
        assert initialized["result"]["protocolVersion"] == "2.0", initialized
        manifest = rpc("describe", "describe-first")["result"]
        assert manifest["version"] == version, manifest
        assert manifest["description"] and isinstance(manifest["tools"], list)
        assert {t["name"] for t in manifest["tools"]} == {"ping", "check_invoice"}
        for tool in manifest["tools"]:
            assert isinstance(tool["parameters"], list), tool
        assert rpc("describe", 2)["result"] == manifest
        assert rpc("health", 3)["result"]["status"] == "ready"
        assert rpc("invoke", 4, {"tool": "ping", "arguments": {}})["result"]["data"]["pong"]
        invoice = {
            "invoice_number": "RELEASE-CHECK", "items": [
                {"quantity": 0.333, "unit_price": 3, "amount": 1}
            ], "subtotal": 1, "tax_rate": 10, "tax": 0.1, "total": 1.1,
        }
        passed = rpc("invoke", 5, {"tool": "check_invoice", "arguments": invoice})["result"]
        assert passed["success"] and passed["data"]["valid"], passed
        invoice["total"] = 1.11
        failed = rpc("invoke", 6, {"tool": "check_invoice", "arguments": invoice})["result"]
        assert failed["success"] and not failed["data"]["valid"], failed
        invalid = rpc("invoke", 7, {"tool": "check_invoice", "arguments": {}})["result"]
        assert invalid["success"] is False, invalid
        assert "error" in rpc("unknown-method", 8)
        assert rpc("describe", "after-errors")["result"] == manifest
        assert process.poll() is None, "Executable exited before stdin EOF"
        process.stdin.close()
        assert process.wait(timeout=5) == 0, "Unclean EOF shutdown"
        assert replies.get(timeout=2) is None, "Unexpected extra stdout"
        print(f"PASS: {version}; describe, health, ping, PASS/FAIL, recovery, EOF")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable")
    parser.add_argument("--version", default="0.3.0")
    args = parser.parse_args()
    artifact = Path(args.executable).resolve(strict=True)
    if tarfile.is_tarfile(artifact):
        with tempfile.TemporaryDirectory(prefix="invoice-release-") as directory:
            with tarfile.open(artifact) as archive:
                archive.extractall(directory, filter="data")
            root = Path(directory)
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            entrypoint = (root / manifest["runtime"]["binary"]["entrypoint"]).resolve()
            assert entrypoint.is_relative_to(root.resolve()), "Entrypoint escapes archive"
            verify(entrypoint, args.version)
    else:
        verify(artifact, args.version)

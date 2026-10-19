"""Run a manifest through the real HTTP service, without reading an answer key.

Usage: python3 scripts/verify_integrated_intake.py MANIFEST --workspace /tmp/unique-run
The manifest contains only `references` and `files` (absolute DOCX paths).
Originals, queue, duplicate delivery and cold process restart are verified.
Results are written before any external comparison with expected outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def multipart(paths):
    boundary = "chug-independent-acceptance-boundary"
    body = b""
    for path in paths:
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
                 'Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n').encode()
        body += path.read_bytes() + b"\r\n"
    return body + f"--{boundary}--\r\n".encode(), boundary


def run(manifest_path, workspace):
    # A fresh workspace is required so earlier queue entries cannot inflate success counts.
    workspace.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(manifest_path.read_text())
    if set(manifest) != {"references", "files"}:
        raise ValueError("Only source references and incoming paths belong in the runtime manifest")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    log = (workspace / "http.log").open("w")
    process = None

    def get(path):
        with urlopen(base + path, timeout=10) as response:
            return response.read()

    def upload(path, paths):
        body, boundary = multipart(paths)
        request = Request(base + path, body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urlopen(request, timeout=20) as response:
            return json.load(response)

    def start():
        nonlocal process
        process = subprocess.Popen([sys.executable, "-m", "chug.server", "--port", str(port),
                                    "--state-dir", str(workspace / "state")], cwd=ROOT, stdout=log, stderr=log)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Service exited; inspect http.log")
            try:
                get("/api/queue")
                return
            except OSError:
                time.sleep(.05)
        raise RuntimeError("Service did not start")

    def stop():
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)

    try:
        start()
        registered = [upload("/api/reference/upload", [Path(p)])["library_item"] for p in manifest["references"]]
        paths = [Path(p) for p in manifest["files"]]
        batch = upload("/api/intakes/batch", paths)
        captures = []
        for path, item in zip(paths, batch["items"]):
            sha = digest(path.read_bytes())
            assert item["sha256"] == sha
            detail = json.loads(get("/api/intakes/" + sha))
            assert digest(get(detail["original_url"])) == sha
            assert detail["human_decision"]["status"] == "pending"
            assert not detail.get("reference_confirmation")
            if detail["reference"]["reference_id"]:
                reference_bytes = get("/api/reference-library/" + detail["reference"]["reference_id"] + "/original")
                assert digest(reference_bytes) == detail["reference"]["sha256"]
            captures.append(detail)
        queue = json.loads(get("/api/queue"))["items"]
        assert len([row for row in queue if row.get("intake")]) == len(paths)
        # Check a cold process restart, then deliver the whole batch again.
        stop()
        start()
        for before in captures:
            after = json.loads(get("/api/intakes/" + before["incoming"]["sha256"]))
            assert after == before
        repeated = upload("/api/intakes/batch", paths)
        assert repeated["counts"]["duplicate"] == len(paths)
        assert [row["id"] for row in repeated["items"]] == [row["id"] for row in batch["items"]]
        result = {"registered": registered, "batch": batch, "captures": captures,
                  "restart_identical": True, "originals_verified": True, "repeat": repeated}
        output = workspace / "captured-results.json"
        output.write_text(json.dumps(result, indent=2))
        print(json.dumps({"batch": batch["counts"], "restart_identical": True,
                          "duplicates": repeated["counts"]["duplicate"], "capture_sha256": digest(output.read_bytes())}))
        return result
    finally:
        stop()
        log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    run(args.manifest.resolve(), args.workspace.resolve())

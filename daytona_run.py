"""Launch one isolated optimiser round in a Daytona sandbox.

The script reads API keys from the ignored local .env file.  It transfers the source video and
the current working tree to Daytona, but never copies .env or writes either key to the repository.

    python3 daytona_run.py --video ~/Downloads/volleyball-annotated/full-001.mp4
"""
import argparse
import os
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REMOTE_ROOT = "workspace/vlm-optimizer"
REMOTE_VIDEO = "workspace/volleyball-annotated/full-001.mp4"
EXCLUDED_DIRS = {".git", ".venv", ".daytona-venv", "__pycache__", "cache", "chunks", "variants"}
EXCLUDED_SUFFIXES = {".pyc", ".log"}


def load_env(path: Path) -> None:
    """Load simple KEY=VALUE entries without printing their values."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def build_archive() -> Path:
    fd, name = tempfile.mkstemp(prefix="vlm-optimizer-", suffix=".tar.gz")
    os.close(fd)
    archive = Path(name)
    with tarfile.open(archive, "w:gz") as tar:
        for path in ROOT.rglob("*"):
            relative = path.relative_to(ROOT)
            if any(part in EXCLUDED_DIRS for part in relative.parts):
                continue
            if path.name == ".env" or path.suffix in EXCLUDED_SUFFIXES:
                continue
            tar.add(path, arcname=relative, recursive=False)
    return archive


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is missing; add it to {ROOT / '.env'}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True, help="local full-match video")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--budget", type=float, default=9.0)
    parser.add_argument("--name", default="vlm-optimizer")
    parser.add_argument("--sandbox-id", help="resume setup in an existing Daytona sandbox")
    args = parser.parse_args()

    load_env(ROOT / ".env")
    require("DAYTONA_API_KEY")
    gemini_key = require("GEMINI_API_KEY")
    if not args.video.is_file():
        raise SystemExit(f"video not found: {args.video}")

    try:
        from daytona import Daytona, CreateSandboxFromSnapshotParams, Resources
    except ImportError as exc:
        raise SystemExit("Install the launcher dependency first: python3 -m pip install daytona") from exc

    daytona = Daytona()
    sandbox = daytona.get(args.sandbox_id) if args.sandbox_id else daytona.create(
        CreateSandboxFromSnapshotParams(
            name=args.name,
            language="python",
            resources=Resources(cpu=4, memory=8, disk=30),
            env_vars={"GEMINI_API_KEY": gemini_key, "VLM_VIDEO_PATH": REMOTE_VIDEO},
            auto_stop_interval=120,
            auto_delete_interval=180,
        ),
        timeout=180,
    )
    print(f"Daytona sandbox: {sandbox.id}")

    archive = build_archive()
    try:
        sandbox.fs.upload_file(archive.read_bytes(), "workspace/vlm-optimizer.tgz")
        unpack = sandbox.process.exec(
            f"mkdir -p {REMOTE_ROOT} && tar -xzf workspace/vlm-optimizer.tgz -C {REMOTE_ROOT}",
            timeout=60,
        )
        if unpack.exit_code:
            raise SystemExit(unpack.result)
    finally:
        archive.unlink(missing_ok=True)

    total = args.video.stat().st_size
    last_percent = -5

    def progress(update):
        nonlocal last_percent
        percent = int(getattr(update, "bytes_sent", 0) * 100 / total)
        if percent >= last_percent + 5 or percent == 100:
            last_percent = percent
            print(f"Uploaded {percent}%", flush=True)

    print(f"Uploading {args.video.name} ({total / 1e9:.2f} GB)…", flush=True)
    sandbox.fs.create_folder("workspace/volleyball-annotated", "755")
    sandbox.fs.upload_file_stream(str(args.video), REMOTE_VIDEO, timeout=0,
                                  on_progress=progress)

    setup = sandbox.process.exec(
        "python3 -m pip install --disable-pip-version-check google-genai opencv-python-headless numpy",
        cwd=REMOTE_ROOT,
        timeout=900,
    )
    if setup.exit_code:
        raise SystemExit(setup.result)

    command = (
        f"nohup python3 -u mutator/mutator.py --rounds {args.rounds} --budget {args.budget} "
        "> optimiser.log 2>&1 & echo $!"
    )
    started = sandbox.process.exec(command, cwd=REMOTE_ROOT, timeout=30)
    if started.exit_code:
        raise SystemExit(started.result)
    print(f"Optimiser started (PID {started.result.strip()}).")
    print(f"Logs: {REMOTE_ROOT}/optimiser.log")


if __name__ == "__main__":
    main()

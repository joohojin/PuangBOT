import argparse
import importlib.metadata
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
REQUIREMENTS_FILE = PROJECT_DIR / "requirements.txt"

IMPORT_NAME_OVERRIDES = {
    "discord.py": "discord",
    "pynacl": "nacl",
    "audioop-lts": "audioop",
    "yt-dlp": "yt_dlp",
    "edge-tts": "edge_tts",
    "gtts": "gtts",
    "pillow": "PIL",
}


def run_command(args, check=False):
    print("[PuangBOT bootstrap] " + " ".join(str(part) for part in args))
    return subprocess.run(args, cwd=PROJECT_DIR, check=check)


def ensure_pip():
    result = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        cwd=PROJECT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode == 0:
        return True

    print("[PuangBOT bootstrap] pip is missing. Trying ensurepip...")
    result = run_command([sys.executable, "-m", "ensurepip", "--upgrade"])
    if result.returncode != 0:
        print("[PuangBOT bootstrap] Failed to install pip.")
        return False

    return subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        cwd=PROJECT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def load_requirement_objects():
    if not REQUIREMENTS_FILE.exists():
        print(f"[PuangBOT bootstrap] Missing {REQUIREMENTS_FILE.name}.")
        return []

    from pip._vendor.packaging.markers import default_environment
    from pip._vendor.packaging.requirements import Requirement

    env = default_environment()
    requirements = []
    for raw_line in REQUIREMENTS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        req = Requirement(line)
        if req.marker and not req.marker.evaluate(env):
            continue
        requirements.append(req)
    return requirements


def module_name_for(package_name):
    key = package_name.lower()
    return IMPORT_NAME_OVERRIDES.get(key, key.replace("-", "_").replace(".", "_"))


def requirement_is_satisfied(req):
    try:
        version = importlib.metadata.version(req.name)
    except importlib.metadata.PackageNotFoundError:
        module_name = module_name_for(req.name)
        if importlib.util.find_spec(module_name) is not None:
            return True, f"{req.name}: import {module_name} OK"
        return False, f"{req.name}: missing"

    if req.specifier and not req.specifier.contains(version, prereleases=True):
        return False, f"{req.name}: installed {version}, required {req.specifier}"
    return True, f"{req.name}: {version} OK"


def find_unsatisfied_requirements():
    requirements = load_requirement_objects()
    unsatisfied = []
    for req in requirements:
        ok, message = requirement_is_satisfied(req)
        print("[PuangBOT bootstrap] " + message)
        if not ok:
            unsatisfied.append(str(req))
    return unsatisfied


def install_requirements():
    if not REQUIREMENTS_FILE.exists():
        return False
    result = run_command([
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--upgrade-strategy",
        "only-if-needed",
        "-r",
        str(REQUIREMENTS_FILE),
    ])
    return result.returncode == 0


def ensure_ffmpeg(check_only=False):
    ffmpeg_name = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
    local_ffmpeg = PROJECT_DIR / ffmpeg_name
    if local_ffmpeg.exists() or shutil.which("ffmpeg"):
        print("[PuangBOT bootstrap] ffmpeg: OK")
        return True

    if platform.system() != "Windows":
        print("[PuangBOT bootstrap] ffmpeg is missing. Install it with your OS package manager.")
        return False

    if check_only:
        print("[PuangBOT bootstrap] ffmpeg.exe: missing")
        return False

    print("[PuangBOT bootstrap] ffmpeg.exe is missing. Downloading local copy...")
    url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = Path(temp_dir) / "ffmpeg.zip"
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, "r") as archive:
            ffmpeg_members = [
                name for name in archive.namelist()
                if name.replace("\\", "/").endswith("/ffmpeg.exe")
            ]
            if not ffmpeg_members:
                print("[PuangBOT bootstrap] Could not find ffmpeg.exe in downloaded archive.")
                return False
            with archive.open(ffmpeg_members[0]) as source, local_ffmpeg.open("wb") as target:
                shutil.copyfileobj(source, target)
    print("[PuangBOT bootstrap] ffmpeg.exe: installed")
    return True


def warn_optional_tools():
    if shutil.which("tesseract"):
        print("[PuangBOT bootstrap] tesseract OCR: OK")
    else:
        print("[PuangBOT bootstrap] tesseract OCR: not found (image OCR fallback may be limited)")

    docker = shutil.which("docker")
    if docker:
        print("[PuangBOT bootstrap] docker: OK")
    else:
        print("[PuangBOT bootstrap] docker: not found (local SearXNG auto-start will be skipped or fail)")


def main():
    parser = argparse.ArgumentParser(description="Prepare PuangBOT runtime dependencies.")
    parser.add_argument("--check-only", action="store_true", help="Only check dependencies; do not install.")
    parser.add_argument("--force", action="store_true", help="Run pip install -r requirements.txt even if checks pass.")
    parser.add_argument("--skip-ffmpeg", action="store_true", help="Do not check or download ffmpeg.exe.")
    args = parser.parse_args()

    os.chdir(PROJECT_DIR)

    if not ensure_pip():
        return 1

    try:
        unsatisfied = find_unsatisfied_requirements()
    except Exception as exc:
        print(f"[PuangBOT bootstrap] Requirement check failed: {exc}")
        unsatisfied = ["requirements.txt"]

    if args.force or unsatisfied:
        if args.check_only:
            print("[PuangBOT bootstrap] Missing or outdated Python packages were found.")
            return 1
        print("[PuangBOT bootstrap] Installing Python packages from requirements.txt...")
        if not install_requirements():
            print("[PuangBOT bootstrap] Python package installation failed.")
            return 1
        remaining = find_unsatisfied_requirements()
        if remaining:
            print("[PuangBOT bootstrap] Some requirements are still missing: " + ", ".join(remaining))
            return 1
    else:
        print("[PuangBOT bootstrap] Python packages already satisfy requirements.txt.")

    if not args.skip_ffmpeg and not ensure_ffmpeg(check_only=args.check_only):
        return 1

    warn_optional_tools()
    print("[PuangBOT bootstrap] Runtime check complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

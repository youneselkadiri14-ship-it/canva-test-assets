"""
process_course.py

Runs the full spacer-clip pipeline across an entire course in one go:
  1. Recursively finds every capsule folder (any folder containing
     voiceover_slide_XXX.mp3 files) under the given course root.
  2. Generates matching spacer_slide_XXX.mp4 clips for each capsule
     (skips any that already match, same as generate_spacers.py).
  3. Copies all spacer clips into the local canva-test-assets repo clone,
     mirroring each capsule's path relative to the course root.
  4. Does ONE git pull/commit/push for the whole batch.
  5. Prints the public raw.githubusercontent.com URL for every spacer clip,
     grouped by capsule.

Usage:
    python process_course.py <course_root_folder> <repo_folder>

Example:
    python process_course.py ^
        "C:\\Users\\Ultrapc\\Desktop\\santé digital script" ^
        "C:\\Users\\Ultrapc\\Desktop\\canva-test-assets"

Notes:
- This does NOT assume any fixed folder naming/depth (like R1/R1_C1).
  It just looks for folders that directly contain voiceover_slide_*.mp3
  files, so it keeps working regardless of how a given course is organized.
- Each capsule's spacer clips are published to the repo at the same
  relative path they have under the course root.
"""

import sys
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_spacers import AUDIO_PATTERN, DURATION_TOLERANCE, get_duration, make_spacer_clip  # noqa: E402

GITHUB_USER = "youneselkadiri14-ship-it"
GITHUB_REPO = "canva-test-assets"
GITHUB_BRANCH = "main"


def find_capsule_folders(course_root: Path):
    """Find every folder anywhere under course_root that directly contains
    voiceover_slide_*.mp3 files."""
    capsule_folders = set()
    for f in course_root.rglob("*.mp3"):
        if AUDIO_PATTERN.match(f.name):
            capsule_folders.add(f.parent)
    return sorted(capsule_folders)


def generate_for_capsule(capsule_folder: Path):
    spacers_folder = capsule_folder / "spacers"
    spacers_folder.mkdir(exist_ok=True)

    audio_files = sorted(
        (f for f in capsule_folder.iterdir() if AUDIO_PATTERN.match(f.name)),
        key=lambda f: int(AUDIO_PATTERN.match(f.name).group(1)),
    )

    made, skipped = 0, 0
    for audio_file in audio_files:
        slide_num = AUDIO_PATTERN.match(audio_file.name).group(1)
        spacer_path = spacers_folder / f"spacer_slide_{slide_num}.mp4"
        audio_duration = get_duration(audio_file)

        if spacer_path.exists():
            existing_duration = get_duration(spacer_path)
            if abs(existing_duration - audio_duration) < DURATION_TOLERANCE:
                skipped += 1
                continue

        make_spacer_clip(audio_duration, spacer_path)
        made += 1

    return spacers_folder, made, skipped


def run(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0 and "nothing to commit" not in result.stdout:
        print(f"Command failed: {' '.join(cmd)}")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    return result.stdout


def main():
    if len(sys.argv) != 3:
        print("Usage: python process_course.py <course_root_folder> <repo_folder>")
        sys.exit(1)

    course_root = Path(sys.argv[1]).resolve()
    repo_folder = Path(sys.argv[2]).resolve()

    if not course_root.is_dir():
        print(f"Error: folder not found: {course_root}")
        sys.exit(1)

    capsule_folders = find_capsule_folders(course_root)
    if not capsule_folders:
        print(f"No capsule folders (with voiceover_slide_*.mp3 files) found under {course_root}")
        sys.exit(1)

    print(f"Found {len(capsule_folders)} capsule folder(s) under {course_root}\n")

    all_urls = {}  # capsule relative path -> list of urls

    for capsule_folder in capsule_folders:
        rel_path = capsule_folder.relative_to(course_root)
        print(f"[{rel_path}]")

        spacers_folder, made, skipped = generate_for_capsule(capsule_folder)
        print(f"  generated {made}, skipped {skipped} (already up to date)")

        dest_folder = repo_folder / rel_path
        dest_folder.mkdir(parents=True, exist_ok=True)

        spacer_files = sorted(spacers_folder.glob("spacer_slide_*.mp4"))
        for f in spacer_files:
            shutil.copy2(f, dest_folder / f.name)

        base_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"
        all_urls[str(rel_path)] = [
            f"{base_url}/{rel_path.as_posix()}/{f.name}" for f in spacer_files
        ]
        print()

    print("Pulling latest changes...")
    run(["git", "pull"], cwd=repo_folder)

    print("Staging and committing...")
    run(["git", "add", "."], cwd=repo_folder)
    run(["git", "commit", "-m", f"Add spacer clips for {len(capsule_folders)} capsule(s)"], cwd=repo_folder)

    print("Pushing...")
    run(["git", "push"], cwd=repo_folder)

    print("\nDone. Public URLs by capsule:\n")
    for rel_path, urls in all_urls.items():
        print(f"[{rel_path}]")
        for url in urls:
            print(f"  {url}")
        print()


if __name__ == "__main__":
    main()

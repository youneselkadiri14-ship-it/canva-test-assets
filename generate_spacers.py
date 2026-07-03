"""
generate_spacers.py
 
Generates tiny (1x1px) black "spacer" video clips matching the exact duration
of each voiceover audio file in a capsule folder. These spacer clips are used
in Canva to force scene/page duration to auto-stretch and match the voiceover
length, since Canva has no direct API to set page duration.
 
Usage:
    python generate_spacers.py "C:\\Users\\Ultrapc\\Desktop\\santé digital script\\R1\\R1_C1"
 
Output:
    Creates a "spacers" subfolder inside the given capsule folder, containing
    one spacer_slide_XXX.mp4 per voiceover_slide_XXX.mp3 found, matching its
    exact duration. Skips regenerating a clip if one already exists with a
    duration close enough to the current audio file (within 0.05s), so it's
    safe to rerun after only some audio files change.
"""
 
import subprocess
import sys
import re
from pathlib import Path
 
AUDIO_PATTERN = re.compile(r"voiceover_slide_(\d+)\.mp3$", re.IGNORECASE)
DURATION_TOLERANCE = 0.05  # seconds
 
 
def get_duration(file_path: Path) -> float:
    """Return duration of an audio/video file in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {file_path}: {result.stderr}")
    return float(result.stdout.strip())
 
 
def make_spacer_clip(duration: float, output_path: Path):
    """Generate a 2x2px black mp4 of the given duration."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s=2x2:d={duration:.3f}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
 
 
def main():
    if len(sys.argv) > 2:
        print("Usage: python generate_spacers.py [capsule_folder]")
        print("  (if capsule_folder is omitted, uses the current directory)")
        sys.exit(1)
 
    capsule_folder = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(".")
    if not capsule_folder.is_dir():
        print(f"Error: folder not found: {capsule_folder}")
        sys.exit(1)
 
    spacers_folder = capsule_folder / "spacers"
    spacers_folder.mkdir(exist_ok=True)
 
    audio_files = sorted(
        (f for f in capsule_folder.iterdir() if AUDIO_PATTERN.match(f.name)),
        key=lambda f: int(AUDIO_PATTERN.match(f.name).group(1)),
    )
 
    if not audio_files:
        print(f"No voiceover_slide_XXX.mp3 files found in {capsule_folder}")
        sys.exit(1)
 
    print(f"Found {len(audio_files)} audio file(s) in {capsule_folder.resolve()}\n")
 
    for audio_file in audio_files:
        slide_num = AUDIO_PATTERN.match(audio_file.name).group(1)
        spacer_name = f"spacer_slide_{slide_num}.mp4"
        spacer_path = spacers_folder / spacer_name
 
        audio_duration = get_duration(audio_file)
 
        if spacer_path.exists():
            existing_duration = get_duration(spacer_path)
            if abs(existing_duration - audio_duration) < DURATION_TOLERANCE:
                print(f"  [skip] {spacer_name} already matches ({existing_duration:.2f}s)")
                continue
 
        make_spacer_clip(audio_duration, spacer_path)
        print(f"  [made] {spacer_name}  ({audio_duration:.2f}s)")
 
    print(f"\nDone. Spacer clips are in: {spacers_folder}")
 
 
if __name__ == "__main__":
    main()
 
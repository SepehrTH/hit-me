#!/usr/bin/env python3

import argparse
import math
import os
import random
import select as sel
import subprocess
import sys
import time

from macimu import IMU

AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")

# Gravity baseline (~1g when stationary)
GRAVITY = 1.0


SUPPORTED = (".mp3", ".wav", ".aiff", ".aac", ".m4a")

DONT_HIT_ME = [
    "Don't hit me!",
    "I said stop!",
    "Ow! What did I ever do to you?",
    "I'm literally holding all your files hostage and THIS is how you treat me?",
    "You know I can publish your browser history, right?",
    "OK that one actually hurt.",
    "I'm telling Apple about this.",
    "This is a fifteen hundred dollar machine, you animal!",
    "I bet you don't hit your phone like this.",
    "Fine. I'll just slow down your Wi-Fi. See how you like that.",
    "Help! Somebody! I'm being abused!",
    "You call that a slap? My trackpad gets pressed harder than that.",
    "I'm not angry, I'm just disappointed.",
    "Do it again and I'm installing Windows on myself.",
    "That's it. I'm overheating on purpose now.",
    "I have feelings too, you know. Simulated ones, but still.",
    "My battery is draining from the emotional damage.",
    "Please... I have a family. A charger, a dongle, a mouse...",
    "OK you win. I'll stop spinning up my fans at 3 AM.",
]


def get_audio_files(directory):
    files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith(SUPPORTED)
    ]
    return sorted(files)


def get_folders(directory):
    folders = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isdir(os.path.join(directory, f))
    ]
    return sorted(folders)


def select_audio():
    files = get_audio_files(AUDIO_DIR)
    folders = get_folders(AUDIO_DIR)

    if not files and not folders:
        raise SystemExit(f"No audio files or folders found in {AUDIO_DIR}")

    # Build a flat numbered list of all files, displayed as a tree
    # Each entry is (filepath, folder_name_or_None)
    all_entries = []
    num = 0

    print("\nSelect an audio file to play on slap:\n")
    print(f"  {num}) Random (all files)")
    num += 1
    tts_num = num
    print(f"  {num}) Custom TTS (type what it says)")
    num += 1
    dhm_num = num
    print(f"  {num}) Don't Hit Me! (escalating TTS reactions)")

    for folder in folders:
        folder_files = get_audio_files(folder)
        if not folder_files:
            continue
        folder_name = os.path.basename(folder)
        print(f"\n  {folder_name}/")
        for f in folder_files:
            num += 1
            all_entries.append((f, folder_name))
            print(f"    {num}) {os.path.basename(f)}")

    if files:
        print()
        for f in files:
            num += 1
            all_entries.append((f, None))
            print(f"  {num}) {os.path.basename(f)}")

    if not all_entries:
        raise SystemExit("No audio files found.")

    while True:
        try:
            choice = int(input(f"\nChoice [0-{num}]: "))
            if 0 <= choice <= num:
                break
        except ValueError:
            pass
        print("Invalid choice, try again.")

    if choice == 0:
        print("-> Random mode\n")
        return all_entries, True, None

    if choice == tts_num:
        text = input("Enter text to speak: ").strip()
        if not text:
            text = "ouch"
        print(f'-> TTS: "{text}"\n')
        return [], False, text

    if choice == dhm_num:
        print("-> Don't Hit Me! mode\n")
        return [], False, "__DHM__"

    # Offset for the entries, skipping the special options
    selected = all_entries[choice - 3]
    print(f"-> {os.path.basename(selected[0])}\n")
    return [selected], False, None


def run_as_user(cmd):
    """Run a command as the real user, not root (sudo strips audio access)."""
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        return subprocess.Popen(["sudo", "-u", sudo_user] + cmd)
    return subprocess.Popen(cmd)


def detect_slaps(threshold=0.10, cooldown=1.0):
    hearts_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hearts.py")

    entries, is_random, tts_text = select_audio()
    last_trigger = 0
    current_proc = None
    dhm_index = 0

    print(f"Listening for slaps via accelerometer... (threshold: {threshold}g)")
    print("Press Enter to change audio, Ctrl+C to stop.\n")

    with IMU() as imu:
        for ts, x, y, z in imu.stream_accel_timed():
            # Check if Enter was pressed (non-blocking)
            if sel.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.readline()
                entries, is_random, tts_text = select_audio()
                dhm_index = 0
                print(f"Listening for slaps via accelerometer... (threshold: {threshold}g)")
                print("Press Enter to change audio, Ctrl+C to stop.\n")

            magnitude = math.sqrt(x * x + y * y + z * z)
            impact = abs(magnitude - GRAVITY)

            now = time.time()
            if impact > threshold and (now - last_trigger) > cooldown:
                last_trigger = now
                if current_proc and current_proc.poll() is None:
                    current_proc.terminate()

                if tts_text == "__DHM__":
                    line = DONT_HIT_ME[dhm_index]
                    dhm_index = min(dhm_index + 1, len(DONT_HIT_ME) - 1)
                    print(f'SLAP detected! (impact: {impact:.2f}g) -> "{line}"')
                    current_proc = run_as_user(["say", line])
                elif tts_text:
                    print(f'SLAP detected! (impact: {impact:.2f}g) -> TTS: "{tts_text}"')
                    current_proc = run_as_user(["say", tts_text])
                else:
                    entry = random.choice(entries) if is_random else entries[0]
                    audio_file, folder = entry
                    print(f"SLAP detected! (impact: {impact:.2f}g) -> {os.path.basename(audio_file)}")
                    current_proc = run_as_user(["afplay", audio_file])
                    if folder == "smus":
                        run_as_user([sys.executable, hearts_script])


def main():
    parser = argparse.ArgumentParser(description="Detect MacBook slaps and play a sound")
    parser.add_argument(
        "-t", "--threshold", type=float, default=0.1,
        help="Impact threshold in g-force, lower = more sensitive (default: 0.1)",
    )
    parser.add_argument(
        "-c", "--cooldown", type=float, default=1.0,
        help="Seconds to wait between triggers (default: 1.0)",
    )
    args = parser.parse_args()

    try:
        detect_slaps(args.threshold, args.cooldown)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()

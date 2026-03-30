#!/usr/bin/env python3
"""Show multiple love.png images floating around the screen."""

import os
import random
import sys
import time

from AppKit import (
    NSApplication,
    NSWindow,
    NSScreen,
    NSBorderlessWindowMask,
    NSBackingStoreBuffered,
    NSColor,
    NSFloatingWindowLevel,
    NSImageView,
    NSImage,
    NSImageScaleProportionallyUpOrDown,
    NSRunLoop,
    NSView,
)
from Foundation import NSMakeRect, NSMakePoint, NSDate

IMGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imgs")
IMAGE_PATH = os.path.join(IMGS_DIR, "love.png")

COUNT = 50
MIN_SIZE = 50
MAX_SIZE = 300
FPS = 60
DURATION = 17


def show_hearts(duration=DURATION):
    time.sleep(4.5)
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(2)

    screen = NSScreen.mainScreen().frame()
    sw, sh = screen.size.width, screen.size.height

    window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(0, 0, sw, sh),
        NSBorderlessWindowMask,
        NSBackingStoreBuffered,
        False,
    )
    window.setLevel_(NSFloatingWindowLevel + 1)
    window.setOpaque_(False)
    window.setBackgroundColor_(NSColor.clearColor())
    window.setIgnoresMouseEvents_(True)

    image = NSImage.alloc().initWithContentsOfFile_(IMAGE_PATH)
    if not image:
        print(f"Could not load image: {IMAGE_PATH}", file=sys.stderr)
        return

    view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, sw, sh))
    window.setContentView_(view)

    # Spawn hearts with random positions, sizes, and velocities
    hearts = []
    for _ in range(COUNT):
        size = random.randint(MIN_SIZE, MAX_SIZE)
        x = random.uniform(0, sw - size)
        y = random.uniform(0, sh - size)
        vx = random.uniform(-150, 150)
        vy = random.uniform(-150, 150)

        iv = NSImageView.alloc().initWithFrame_(NSMakeRect(x, y, size, size))
        iv.setImage_(image)
        iv.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        iv.setAlphaValue_(random.uniform(0.5, 1.0))
        view.addSubview_(iv)

        base_alpha = random.uniform(0.5, 1.0)
        hearts.append({"view": iv, "x": x, "y": y, "vx": vx, "vy": vy, "size": size, "alpha": base_alpha})

    window.makeKeyAndOrderFront_(None)

    # Animate frame by frame
    dt = 1.0 / FPS
    start = time.time()

    while time.time() - start < duration:
        elapsed = time.time() - start
        # Fade out in the last second
        alpha_mult = min(1.0, (duration - elapsed) / 1.0)

        for h in hearts:
            h["x"] += h["vx"] * dt
            h["y"] += h["vy"] * dt

            # Bounce off screen edges
            if h["x"] < 0:
                h["x"] = 0
                h["vx"] *= -1
            elif h["x"] > sw - h["size"]:
                h["x"] = sw - h["size"]
                h["vx"] *= -1

            if h["y"] < 0:
                h["y"] = 0
                h["vy"] *= -1
            elif h["y"] > sh - h["size"]:
                h["y"] = sh - h["size"]
                h["vy"] *= -1

            h["view"].setFrameOrigin_(NSMakePoint(h["x"], h["y"]))
            h["view"].setAlphaValue_(alpha_mult * h["alpha"])

        # Pump the run loop for one frame
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(dt)
        )

    window.orderOut_(None)


if __name__ == "__main__":
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else DURATION
    show_hearts(duration)

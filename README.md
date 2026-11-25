# Touchless AirScroll

A lightweight, webcam-powered touchless scroller built for everyday reading, coding, and browsing without reaching for your trackpad. 

This project includes both a **system-wide Python desktop utility** (works across browsers, PDFs, VS Code, and terminals) and a **zero-install browser demo** powered by MediaPipe WebAssembly.

---

## Live Browser Demo
Want to test it right away without installing anything? Try the interactive Iron Man HUD sandbox directly in your browser (runs 100% locally on your GPU—no video data ever leaves your device):

 **[Launch Live Demo](https://YOUR_USERNAME.github.io/touchless-airscroll/)** *(Replace with your GitHub Pages URL)*

---

## Two Ways to Scroll

1. **Hand Pinch Mode (Virtual Air-Joystick):**
   Pinch your thumb and index finger together to lock an anchor point in mid-air. Slide slightly up or down to control scroll direction and velocity smoothly—no arm fatigue.
2. **Deliberate Blink Mode (Hands-Free Reader):**
   Built for when your hands are busy. Hold one intentional blink (`~0.25s`) to scroll down, or double-blink to scroll back up.

---

## Engineering Notes (v2.0 Upgrades)

After sharing v1 on LinkedIn, a lot of folks asked two great questions: *How do you stop normal blinks from triggering scrolls?* and *How much CPU/battery does it drain?* Here is how v2.0 solves both:

* **Filtering Natural vs. Deliberate Blinks:**  
  A normal involuntary blink lasts roughly `100–150ms`. Instead of triggering on every Eye Aspect Ratio (EAR) drop, the tracker measures closure duration and only registers blinks held between **220ms and 750ms**, followed by a `0.6s` cooldown so normal reading never causes accidental jumps.
* **Low-CPU & Battery-Friendly Pipeline:**
  * Captures frames at `320x240` (reducing pixel processing overhead by 75%).
  * Disables FaceMesh iris refinement (`refine_landmarks=False`) to cut face inference load by ~40%.
  * Caps active tracking at **24 FPS** and automatically drops into a **5 FPS Eco-Sleep** mode after 3 seconds of inactivity.

---

## Quick Start (Desktop App)

> **Note:** Requires **Python 3.9 – 3.12** (MediaPipe's `solutions` API does not yet support Python 3.13+).

### 1. Clone the repository
```bash
git clone https://github.com
cd touchless-airscroll
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the scroller
```bash
python touchless_scroll.py
```

For daily use without the camera preview window cluttering your screen, run it in background mode:
```bash
python touchless_scroll.py --headless
```

*(**macOS users:** Grant your Terminal or IDE permission under **System Settings > Privacy & Security > Accessibility** and **Camera** so `PyAutoGUI` can scroll.)*

---

## ⌨️ Keyboard Controls & Tuning

* **Press `M`** — Switch between **Hand Pinch Mode** and **Deliberate Blink Mode**
* **Press `Q`** — Quit the application

You can easily customize thresholds at the top of `touchless_scroll.py` (`PINCH_THRESHOLD`, `SCROLL_SENSITIVITY`, `EAR_THRESHOLD`, or `MIN_DELIBERATE_BLINK`) to match your lighting and comfort.

---

## Tech Stack
* **Python** (OpenCV, MediaPipe, PyAutoGUI)
* **Web Demo** (Vanilla JS, HTML5 Canvas, MediaPipe Tasks Vision WASM/WebGL)

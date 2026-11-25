import cv2
import mediapipe as mp
import pyautogui
import math
import time
import sys


PINCH_THRESHOLD = 0.05
DEADZONE = 0.025
SCROLL_SENSITIVITY = 750
SMOOTHING = 0.25

EAR_THRESHOLD = 0.21
MIN_DELIBERATE_BLINK = 0.165  
MAX_DELIBERATE_BLINK = 0.65 
DOUBLE_BLINK_WINDOW = 0.38   
COOLDOWN_SECONDS = 0.35       
BLINK_SCROLL_AMOUNT = 420     


ACTIVE_FPS = 24
IDLE_FPS = 5
IDLE_TIMEOUT = 3.0            

SHOW_WINDOW = "--headless" not in sys.argv
pyautogui.PAUSE = 0


mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.72,
    min_tracking_confidence=0.72
)

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=False,   # Disabled iris mesh to save ~40% CPU
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

LEFT_EYE = (33, 160, 158, 133, 153, 144)
RIGHT_EYE = (362, 385, 387, 263, 373, 380)

def calculate_ear(landmarks, eye_indices, w, h):
    x_idx, y_idx = 0, 1
    p0, p1, p2, p3, p4, p5 = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in eye_indices]
    v1 = math.hypot(p1[x_idx] - p5[x_idx], p1[y_idx] - p5[y_idx])
    v2 = math.hypot(p2[x_idx] - p4[x_idx], p2[y_idx] - p4[y_idx])
    horiz = math.hypot(p0[x_idx] - p3[x_idx], p0[y_idx] - p3[y_idx])
    return 0.3 if horiz == 0 else (v1 + v2) / (2.0 * horiz)

def smooth_scroll(amount):
    steps = 5
    step_amount = int(amount / steps)
    for _ in range(steps):
        pyautogui.scroll(step_amount)
        time.sleep(0.005)

# Low-res capture drastically lowers memory & CPU overhead
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

mode = "HAND"
anchor_y = None
smoothed_y = None
scroll_accumulator = 0.0

eye_closed_start = None
blink_count = 0
last_blink_end = 0
cooldown_until = 0
blink_status = "Ready (Hold blink 0.25s)"
blink_color = (200, 200, 200)
status_clear_time = 0

last_detected_time = time.time()
first_idx = 0
thumb_idx, index_idx = 4, 8

print("Touchless Scroll v2.0 (Low-CPU) Active! Press 'M' to switch mode, 'Q' to quit.")

while cap.isOpened():
    loop_start = time.time()
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    now = time.time()
    detected = False

    # ---------------- HAND PINCH MODE ----------------
    if mode == "HAND":
        results = hands.process(rgb_frame)
        status_text = "[HAND] Idle (Pinch to Scroll)"
        status_color = (180, 180, 180)

        if results.multi_hand_landmarks:
            detected = True
            last_detected_time = now
            hand_landmarks = results.multi_hand_landmarks[first_idx]
            lm = hand_landmarks.landmark
            thumb_tip, index_tip = lm[thumb_idx], lm[index_idx]

            pinch_dist = math.hypot(index_tip.x - thumb_tip.x, index_tip.y - thumb_tip.y)
            mid_x = (thumb_tip.x + index_tip.x) / 2
            mid_y = (thumb_tip.y + index_tip.y) / 2

            smoothed_y = mid_y if smoothed_y is None else (SMOOTHING * mid_y) + ((1 - SMOOTHING) * smoothed_y)

            if pinch_dist < PINCH_THRESHOLD:
                if anchor_y is None:
                    anchor_y = smoothed_y

                delta_y = smoothed_y - anchor_y
                if abs(delta_y) > DEADZONE:
                    effective_delta = delta_y - math.copysign(DEADZONE, delta_y)
                    scroll_accumulator += -effective_delta * SCROLL_SENSITIVITY
                    scroll_ticks = int(scroll_accumulator)
                    if scroll_ticks != 0:
                        pyautogui.scroll(scroll_ticks)
                        scroll_accumulator -= scroll_ticks

                    direction = "UP" if scroll_ticks > 0 else "DOWN"
                    status_text = f"[HAND] Scrolling {direction}"
                    status_color = (0, 255, 120)
                else:
                    status_text = "[HAND] Anchored"
                    status_color = (0, 200, 255)

                if SHOW_WINDOW:
                    ax, ay = int(mid_x * w), int(anchor_y * h)
                    cx, cy = int(mid_x * w), int(smoothed_y * h)
                    cv2.circle(frame, (ax, ay), 6, (0, 200, 255), 2)
                    cv2.circle(frame, (cx, cy), 6, status_color, -1)
                    cv2.line(frame, (ax, ay), (cx, cy), status_color, 2)
            else:
                anchor_y = None
                scroll_accumulator = 0.0

            if SHOW_WINDOW:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        else:
            anchor_y = None
            smoothed_y = None
            scroll_accumulator = 0.0

    # ---------------- DELIBERATE BLINK MODE ----------------
    elif mode == "BLINK":
        results = face_mesh.process(rgb_frame)
        if results.multi_face_landmarks:
            detected = True
            last_detected_time = now
            lm = results.multi_face_landmarks[first_idx].landmark
            avg_ear = (calculate_ear(lm, LEFT_EYE, w, h) + calculate_ear(lm, RIGHT_EYE, w, h)) / 2.0

            if SHOW_WINDOW:
                for idx in LEFT_EYE + RIGHT_EYE:
                    cv2.circle(frame, (int(lm[idx].x * w), int(lm[idx].y * h)), 1, (0, 255, 255), -1)

            if now >= cooldown_until:
                if avg_ear < EAR_THRESHOLD:
                    if eye_closed_start is None:
                        eye_closed_start = now
                else:
                    if eye_closed_start is not None:
                        closed_duration = now - eye_closed_start
                        # Only count deliberate blinks (filters out fast natural reflexes)
                        if MIN_DELIBERATE_BLINK <= closed_duration <= MAX_DELIBERATE_BLINK:
                            blink_count += 1
                            last_blink_end = now
                        eye_closed_start = None

                if blink_count > 0 and (now - last_blink_end) > DOUBLE_BLINK_WINDOW:
                    if blink_count == 1:
                        smooth_scroll(-BLINK_SCROLL_AMOUNT)
                        blink_status = "[BLINK] Deliberate 1x -> DOWN"
                        blink_color = (0, 200, 255)
                    elif blink_count >= 2:
                        smooth_scroll(BLINK_SCROLL_AMOUNT)
                        blink_status = "[BLINK] Deliberate 2x -> UP"
                        blink_color = (0, 255, 120)
                    blink_count = 0
                    cooldown_until = now + COOLDOWN_SECONDS
                    status_clear_time = now + 1.2

        if now > status_clear_time and blink_count == 0:
            blink_status = "[BLINK] Ready (Hold blink ~0.25s)"
            blink_color = (200, 200, 200)

        status_text, status_color = blink_status, blink_color

    # ---------------- ADAPTIVE POWER SAVER ----------------
    is_eco_sleep = (now - last_detected_time) > IDLE_TIMEOUT
    target_fps = IDLE_FPS if is_eco_sleep else ACTIVE_FPS

    if SHOW_WINDOW:
        hud_label = f"{status_text} | {'ECO 5FPS' if is_eco_sleep else '24FPS'}"
        cv2.rectangle(frame, (6, 6), (w - 6, 36), (20, 20, 20), -1)
        cv2.putText(frame, hud_label, (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.42, status_color, 1)
        cv2.putText(frame, "'M': Mode | 'Q': Quit", (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1)
        cv2.imshow("Touchless AirScroll v2", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('m'):
            mode = "BLINK" if mode == "HAND" else "HAND"
            anchor_y = None
            blink_count = 0
            eye_closed_start = None

    # Sleep remaining frame budget to keep CPU usage minimal
    elapsed = time.time() - loop_start
    sleep_time = max(0.0, (1.0 / target_fps) - elapsed)
    if sleep_time > 0:
        time.sleep(sleep_time)

cap.release()
cv2.destroyAllWindows()

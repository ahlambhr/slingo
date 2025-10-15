import cv2
import numpy as np
import time
from collections import deque, Counter
from tensorflow.keras.models import load_model
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import mediapipe as mp

# === Load model and label map
model = load_model("models/asl_model.h5")
label_map = np.load("models/label_map.npy", allow_pickle=True).item()

# === MediaPipe setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.6)
mp_draw = mp.solutions.drawing_utils

# === Font
try:
    font = ImageFont.truetype("arial.ttf", 40)
except:
    font = ImageFont.load_default()

# === Config
img_size = 128
prediction_buffer = deque(maxlen=15)
current_word = ""
current_sentence = ""
last_added_letter = ""
last_letter_time = time.time()
WORD_TIMEOUT = 2.5

# === Start webcam
cap = cv2.VideoCapture(0)
print("✋ Arabic Sign Sentence Builder is running...")
print("Controls: [q]=Quit, [r]=Reset, [b]=Backspace")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    letter = ""
    confidence = 0.0
    hand_detected = False

    if results.multi_hand_landmarks:
        hand_detected = True
        h, w, _ = frame.shape
        hand = results.multi_hand_landmarks[0]

        x_coords = [int(lm.x * w) for lm in hand.landmark]
        y_coords = [int(lm.y * h) for lm in hand.landmark]
        x_min, x_max = max(min(x_coords) - 20, 0), min(max(x_coords) + 20, w)
        y_min, y_max = max(min(y_coords) - 20, 0), min(max(y_coords) + 20, h)
        roi = frame[y_min:y_max, x_min:x_max]

        if roi.size > 0:
            resized = cv2.resize(roi, (img_size, img_size))
            normalized = resized / 255.0
            reshaped = normalized.reshape(1, img_size, img_size, 3)

            pred = model.predict(reshaped)
            class_id = np.argmax(pred)
            confidence = np.max(pred)
            letter = label_map[class_id]

            prediction_buffer.append(letter)

            if len(prediction_buffer) == prediction_buffer.maxlen:
                most_common, count = Counter(prediction_buffer).most_common(1)[0]
                if count > 10 and most_common != last_added_letter and confidence > 0.7:
                    current_word += most_common
                    last_added_letter = most_common
                    last_letter_time = time.time()
                    prediction_buffer.clear()

        mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

    if not hand_detected and current_word:
        if time.time() - last_letter_time > WORD_TIMEOUT:
            current_sentence += current_word + " "
            current_word = ""
            last_added_letter = ""

    reshaped_letter = get_display(arabic_reshaper.reshape(letter)) if letter else ""
    reshaped_word = get_display(arabic_reshaper.reshape(current_word))
    reshaped_sentence = get_display(arabic_reshaper.reshape(current_sentence))

    frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(frame_pil)
    draw.text((10, 10), f"الحرف: {reshaped_letter} ({confidence:.2f})", font=font, fill=(0, 255, 0))
    draw.text((10, 60), f"الكلمة: {reshaped_word}", font=font, fill=(255, 255, 0))
    draw.text((10, 110), f"الجملة: {reshaped_sentence}", font=font, fill=(0, 200, 255))
    frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)

    cv2.imshow("📜 Arabic Sign Sentence Builder", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break
    elif key == ord("r"):
        current_word = ""
        current_sentence = ""
        last_added_letter = ""
    elif key == ord("b"):
        current_word = current_word[:-1]

cap.release()
cv2.destroyAllWindows()

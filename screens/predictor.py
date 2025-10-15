# screens/predictor.py

import os
import time
from collections import deque, Counter

import cv2
import numpy as np
import arabic_reshaper
from bidi.algorithm import get_display

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.graphics import Color, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import Screen

import mediapipe as mp
from tensorflow.keras.models import load_model

# ─── Register Arabic font ──────────────────────────────────────────────────────
LabelBase.register(name="Amiri", fn_regular="fonts/Amiri-Regular.ttf")


def rtl(text: str) -> str:
    """
    Reshape Arabic text for right-to-left display.
    """
    return get_display(arabic_reshaper.reshape(text))


class IconButton(ButtonBehavior, KivyImage):
    """
    A tappable Image button.
    """
    pass


class PredictorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ─── Load ML model & Mediapipe setup ───────────────────────────────────
        self.model = load_model("models/asl_model.h5")
        self.label_map = np.load("models/label_map.npy", allow_pickle=True).item()
        self.img_size = 128

        # Camera capture (live) and video capture (imported)
        self.cap = None
        self.video_cap = None
        self.is_video_mode = False

        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.6,
        )
        self.mp_draw = mp.solutions.drawing_utils

        self.prediction_buffer = deque(maxlen=15)
        self.current_word = ""
        self.current_sentence = ""
        self.last_added_letter = ""
        self.last_letter_time = time.time()
        self.WORD_TIMEOUT = 2.5

        # ─────────────────────────────────────────────────────────────────────
        # ROOT LAYOUT
        # ─────────────────────────────────────────────────────────────────────
        self.root_layout = BoxLayout(orientation="vertical")
        self.add_widget(self.root_layout)

        # ─────────────────────────────────────────────────────────────────────
        # 1) HEADER BAR (orange background + “Slingo”)
        # ─────────────────────────────────────────────────────────────────────
        header = BoxLayout(size_hint_y=None, height=70)
        with header.canvas.before:
            Color(1, 0.5, 0.1, 1)  # Bright orange
            self.header_rect = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda w, *_: setattr(self.header_rect, "pos", w.pos))
        header.bind(size=lambda w, *_: setattr(self.header_rect, "size", w.size))

        self.logo_label = Label(
            text="Slingo",
            font_name="Amiri",
            font_size=44,
            bold=True,
            color=(0.03, 0.05, 0.15, 1),
            halign="left",
            valign="middle",
            size_hint=(1, 1),
            padding=(20, 0),
        )
        self.logo_label.bind(size=self.logo_label.setter("text_size"))
        header.add_widget(self.logo_label)
        self.root_layout.add_widget(header)

        # ─────────────────────────────────────────────────────────────────────
        # 2) “Back to Home” BUTTON
        # ─────────────────────────────────────────────────────────────────────
        self.back_btn = IconButton(
            source="assets/icons/angle-double-left.png",
            size_hint=(None, None),
            size=(50, 50),
            allow_stretch=True,
        )
        back_anchor = AnchorLayout(
            size_hint_y=None, height=60, anchor_x="left", anchor_y="center"
        )
        back_anchor.add_widget(self.back_btn)
        self.root_layout.add_widget(back_anchor)

        # ─────────────────────────────────────────────────────────────────────
        # 3) SWITCH BAR CARD
        # ─────────────────────────────────────────────────────────────────────
        switch_anchor = AnchorLayout(size_hint_y=None, height=90)
        switch_wrapper = BoxLayout(size_hint=(0.9, None), height=60)
        with switch_wrapper.canvas.before:
            Color(0, 0, 0, 0.18)  # Shadow
            self.switch_shadow = RoundedRectangle(
                pos=(switch_wrapper.x + 4, switch_wrapper.y - 4),
                size=(switch_wrapper.width, switch_wrapper.height),
                radius=[40, 40, 40, 40],
            )
            Color(1, 1, 1, 1)  # White background
            self.switch_bg_card = RoundedRectangle(
                pos=switch_wrapper.pos,
                size=switch_wrapper.size,
                radius=[40, 40, 40, 40],
            )
        switch_wrapper.bind(
            pos=lambda w, *_: (
                setattr(self.switch_bg_card, "pos", w.pos),
                setattr(self.switch_shadow, "pos", (w.x + 4, w.y - 4)),
            )
        )
        switch_wrapper.bind(
            size=lambda w, *_: (
                setattr(self.switch_bg_card, "size", w.size),
                setattr(self.switch_shadow, "size", w.size),
            )
        )

        switch_container = BoxLayout(
            orientation="horizontal", size_hint=(1, 1), padding=(4, 0), spacing=0
        )

        self.btn_language = Button(
            text=rtl("لغة"),
            font_name="Amiri",
            font_size=26,
            bold=True,
            background_normal="",
            background_color=(1, 1, 1, 1),
            color=(0.6, 0.6, 0.6, 1),
            size_hint=(0.45, 1),
        )
        self.btn_language.bind(on_release=lambda *_: self._switch_to_language())

        self.btn_toggle = IconButton(
            source="assets/icons/switch.png",
            size_hint=(None, None),
            size=(50, 50),
            allow_stretch=True,
            keep_ratio=True,
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self.btn_toggle.bind(on_release=lambda *_: self.toggle_mode())

        middle_holder = FloatLayout(size_hint=(0.10, 1))
        middle_holder.add_widget(self.btn_toggle)

        self.btn_sign = Button(
            text=rtl("إشارة"),
            font_name="Amiri",
            font_size=26,
            bold=True,
            background_normal="",
            background_color=(1, 0.5, 0.0, 1),
            color=(0.93, 0.90, 0.97, 1),
            size_hint=(0.45, 1),
        )
        self.btn_sign.bind(on_release=lambda *_: self._switch_to_sign())

        switch_container.add_widget(self.btn_language)
        switch_container.add_widget(middle_holder)
        switch_container.add_widget(self.btn_sign)
        switch_wrapper.add_widget(switch_container)
        switch_anchor.add_widget(switch_wrapper)
        self.root_layout.add_widget(switch_anchor)

        # ─────────────────────────────────────────────────────────────────────
        # 4) MIDDLE AREA: Detection + Output Boxes
        # ─────────────────────────────────────────────────────────────────────
        middle_container = BoxLayout(
            orientation="vertical", size_hint_y=1, spacing=4, padding=(0, 0, 0, 200)
        )
        self.root_layout.add_widget(middle_container)

        # 4.a) DETECTION CARD
        detect_anchor = AnchorLayout(size_hint_y=None, height=360)
        detect_card = BoxLayout(size_hint=(0.9, None), height=340)
        with detect_card.canvas.before:
            Color(0, 0, 0, 0.18)  # Shadow
            self.detect_shadow = RoundedRectangle(
                pos=(detect_card.x + 5, detect_card.y - 5),
                size=(detect_card.width, detect_card.height),
                radius=[40, 40, 40, 40],
            )
            Color(1, 0.9, 0.7, 1)  # Light orange
            self.detect_bg = RoundedRectangle(
                pos=detect_card.pos,
                size=detect_card.size,
                radius=[40, 40, 40, 40],
            )
            Color(0.85, 0.85, 0.85, 1)  # Border
            self.detect_border = RoundedRectangle(
                pos=(detect_card.x + 2, detect_card.y + 2),
                size=(detect_card.width - 4, detect_card.height - 4),
                radius=[40, 40, 40, 40],
            )
        detect_card.bind(
            pos=lambda w, *_: (
                setattr(self.detect_bg, "pos", w.pos),
                setattr(self.detect_shadow, "pos", (w.x + 5, w.y - 5)),
                setattr(self.detect_border, "pos", (w.x + 2, w.y + 2)),
            )
        )
        detect_card.bind(
            size=lambda w, *_: (
                setattr(self.detect_bg, "size", w.size),
                setattr(self.detect_shadow, "size", w.size),
                setattr(self.detect_border, "size", (w.width - 4, w.height - 4)),
            )
        )

        self.img_widget = KivyImage(size_hint=(1, 1), allow_stretch=True, keep_ratio=False)
        detect_card.add_widget(self.img_widget)
        detect_anchor.add_widget(detect_card)
        middle_container.add_widget(detect_anchor)

        # 4.b) TEXT OUTPUT CARD (with trash icon)
        text_anchor = AnchorLayout(size_hint_y=None, height=180)
        text_card = FloatLayout(size_hint=(0.9, None), height=160)
        with text_card.canvas.before:
            Color(0, 0, 0, 0.18)  # Shadow
            self.out_shadow = RoundedRectangle(
                pos=(text_card.x + 5, text_card.y - 5),
                size=(text_card.width, text_card.height),
                radius=[40, 40, 40, 40],
            )
            Color(1, 0.9, 0.7, 1)  # Light orange
            self.out_bg = RoundedRectangle(
                pos=text_card.pos,
                size=text_card.size,
                radius=[40, 40, 40, 40],
            )
            Color(0.85, 0.85, 0.85, 1)  # Border
            self.out_border = RoundedRectangle(
                pos=(text_card.x + 2, text_card.y + 2),
                size=(text_card.width - 4, text_card.height - 4),
                radius=[40, 40, 40, 40],
            )
        text_card.bind(
            pos=lambda w, *_: (
                setattr(self.out_bg, "pos", w.pos),
                setattr(self.out_shadow, "pos", (w.x + 5, w.y - 5)),
                setattr(self.out_border, "pos", (w.x + 2, w.y + 2)),
            )
        )
        text_card.bind(
            size=lambda w, *_: (
                setattr(self.out_bg, "size", w.size),
                setattr(self.out_shadow, "size", w.size),
                setattr(self.out_border, "size", (w.width - 4, w.height - 4)),
            )
        )

        # Label showing الحرف, الكلمة on the first line, and الجملة on the second line
        self.output_label = Label(
            text=rtl("الحرف:  ـ    الكلمة:  ـ") + "\n" + rtl("الجملة:  ـ"),
            font_name="Amiri",
            font_size=28,
            bold=True,
            color=(0.15, 0.15, 0.8, 1),
            halign="right",
            valign="top",
            size_hint=(0.9, 1),      # leave some left padding for the trash icon
            pos_hint={"x": 0.1, "y": 0},
        )
        self.output_label.bind(size=self.output_label.setter("text_size"))
        text_card.add_widget(self.output_label)

        # Trash icon (larger) placed inside the card, top-left corner
        trash_btn = IconButton(
            source="assets/icons/trash.png",
            size_hint=(None, None),
            size=(60, 60),                     # bigger icon
            pos_hint={"x": 0.02, "top": 0.95},  # inside top-left of the card
            allow_stretch=True,
        )
        trash_btn.bind(on_release=self.clear_output)
        text_card.add_widget(trash_btn)

        text_anchor.add_widget(text_card)
        middle_container.add_widget(text_anchor)

        # ─────────────────────────────────────────────────────────────────────
        # 5) BOTTOM NAVIGATION BAR
        # ─────────────────────────────────────────────────────────────────────
        bottom_nav = BoxLayout(size_hint_y=None, height=120, spacing=0, padding=0)
        with bottom_nav.canvas.before:
            Color(0, 0, 0, 0.20)  # Shadow under nav
            self.nav_shadow = RoundedRectangle(
                pos=(bottom_nav.x, bottom_nav.y - 8),
                size=(bottom_nav.width, bottom_nav.height + 8),
                radius=[40, 40, 0, 0],
            )
            Color(1, 0.9, 0.7, 1)  # Light orange background
            self.nav_bg = RoundedRectangle(
                pos=bottom_nav.pos,
                size=bottom_nav.size,
                radius=[40, 40, 0, 0],
            )
        bottom_nav.bind(
            pos=lambda w, *_: (
                setattr(self.nav_bg, "pos", w.pos),
                setattr(self.nav_shadow, "pos", (w.x, w.y - 8)),
            )
        )
        bottom_nav.bind(
            size=lambda w, *_: (
                setattr(self.nav_bg, "size", w.size),
                setattr(self.nav_shadow, "size", (w.width, w.height + 8)),
            )
        )

        def _create_nav_item(icon_path, label_text, callback, is_predict=False):
            container = AnchorLayout(size_hint=(0.2, 1))
            box = BoxLayout(
                orientation="vertical",
                size_hint=(0.8, 1),
                pos_hint={"center_x": 0.5, "center_y": 0.5},
                spacing=4,
            )

            icon_size = (100, 100) if is_predict else (50, 50)
            icon_y_offset = 0.65 if is_predict else 0.6

            icon_btn = IconButton(
                source=icon_path,
                size_hint=(None, None),
                size=icon_size,
                pos_hint={"center_x": 0.5, "center_y": icon_y_offset},
                allow_stretch=True,
            )
            icon_btn.bind(on_release=lambda inst: callback(inst))
            box.add_widget(icon_btn)

            lbl = Label(
                text=label_text,
                font_name="Amiri",
                font_size=24,
                bold=True,
                color=(0.15, 0.15, 0.15, 1),
                size_hint_y=None,
                height=32,
                halign="center",
            )
            lbl.bind(size=lbl.setter("text_size"))
            box.add_widget(lbl)

            container.add_widget(box)
            return container

        camera_item = _create_nav_item(
            icon_path="assets/icons/camera.png",
            label_text=rtl("صورة"),
            callback=self.upload_image,
            is_predict=False,
        )
        predict_item = _create_nav_item(
            icon_path="assets/icons/translate.png",
            label_text=rtl("تعرُّف"),
            callback=self.restart_camera,
            is_predict=True,
        )
        video_item = _create_nav_item(
            icon_path="assets/icons/video.png",
            label_text=rtl("فيديو"),
            callback=self.upload_video,
            is_predict=False,
        )

        # Add empty fillers so the three items stay centered
        filler_left = BoxLayout(size_hint=(0.2, 1))
        filler_right = BoxLayout(size_hint=(0.2, 1))

        for item in (filler_left, camera_item, predict_item, video_item, filler_right):
            bottom_nav.add_widget(item)

        self.root_layout.add_widget(bottom_nav)

    def on_parent(self, instance, parent):
        """
        Called whenever this screen is added to a parent (usually the ScreenManager).
        Bind the back button so it switches to 'home'.
        """
        if parent:
            self.back_btn.bind(on_release=lambda *_: setattr(parent, "current", "home"))

    def _switch_to_language(self):
        if self.manager:
            self.manager.current = "translator"

    def _switch_to_sign(self):
        # Already on the sign→text screen; do nothing
        pass

    def toggle_mode(self):
        if self.manager and self.manager.current == "predictor":
            self.manager.current = "translator"
        else:
            self.manager.current = "predictor"

    def on_enter(self):
        # If a video was playing, stop it and keep last frame visible
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
            self.is_video_mode = False

        # Start live camera
        self.cap = cv2.VideoCapture(0)
        self.event = Clock.schedule_interval(self.update, 1.0 / 30.0)

    def on_leave(self):
        self.stop_camera()

    def stop_camera(self):
        # Release live camera
        if self.cap:
            self.cap.release()
            self.cap = None
        # Release video if open
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
            self.is_video_mode = False
        # Cancel scheduled update
        if hasattr(self, "event"):
            self.event.cancel()

    def restart_camera(self, instance):
        """
        Called by “تعرُّف” button: clear outputs and start camera.
        """
        self.stop_camera()
        self.output_label.text = rtl("الحرف:  ـ    الكلمة:  ـ") + "\n" + rtl("الجملة:  ـ")
        self.current_word = ""
        self.current_sentence = ""
        self.last_added_letter = ""
        self.prediction_buffer.clear()
        self.on_enter()

    def clear_output(self, instance):
        """
        Called by trash icon: clear only the text output (الحرف/الكلمة/الجملة).
        """
        self.current_word = ""
        self.current_sentence = ""
        self.last_added_letter = ""
        self.prediction_buffer.clear()
        self.output_label.text = rtl("الحرف:  ـ    الكلمة:  ـ") + "\n" + rtl("الجملة:  ـ")

    def update(self, dt):
        """
        Called 30×/sec. If in video mode, read from the imported video; else read from camera.
        """
        if self.is_video_mode:
            if not self.video_cap:
                return
            ret, frame = self.video_cap.read()
            if not ret:
                # Video finished → stop updates, keep last frame visible
                self.video_cap.release()
                self.video_cap = None
                self.is_video_mode = False
                if hasattr(self, "event"):
                    self.event.cancel()
                return
            self.predict_from_frame(frame)
        else:
            if not self.cap:
                return
            ret, frame = self.cap.read()
            if not ret:
                return
            self.predict_from_frame(frame)

    def predict_from_frame(self, frame):
        """
        Main prediction logic:
        - Mirror the frame
        - Run Mediapipe hand detection
        - Crop ROI → CNN inference
        - Buffer letters → build word/sentence
        - Update output_label and img_widget.texture
        """
        display_frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        letter = ""
        hand_detected = False

        if results.multi_hand_landmarks:
            hand_detected = True
            h, w, _ = display_frame.shape
            hand = results.multi_hand_landmarks[0]

            x_coords = [int(lm.x * w) for lm in hand.landmark]
            y_coords = [int(lm.y * h) for lm in hand.landmark]
            x_min, x_max = max(min(x_coords) - 50, 0), min(max(x_coords) + 50, w)
            y_min, y_max = max(min(y_coords) - 50, 0), min(max(y_coords) + 50, h)
            roi = display_frame[y_min:y_max, x_min:x_max]

            if roi.size > 0:
                resized = cv2.resize(roi, (self.img_size, self.img_size))
                normalized = resized.astype("float32") / 255.0
                reshaped = normalized.reshape(1, self.img_size, self.img_size, 3)
                pred = self.model.predict(reshaped)
                class_id = np.argmax(pred)
                confidence = np.max(pred)
                letter = self.label_map[class_id]
                self.prediction_buffer.append(letter)

                if (
                    len(self.prediction_buffer) == self.prediction_buffer.maxlen
                    and confidence > 0.7
                ):
                    most_common, count = Counter(self.prediction_buffer).most_common(1)[0]
                    if count > 10 and most_common != self.last_added_letter:
                        self.current_word += most_common
                        self.last_added_letter = most_common
                        self.last_letter_time = time.time()
                        self.prediction_buffer.clear()

            self.mp_draw.draw_landmarks(
                display_frame, hand, mp.solutions.hands.HAND_CONNECTIONS
            )

        if not hand_detected and self.current_word:
            if time.time() - self.last_letter_time > self.WORD_TIMEOUT:
                self.current_sentence += self.current_word + " "
                self.current_word = ""
                self.last_added_letter = ""

        reshaped_letter = rtl(letter)
        reshaped_word = rtl(self.current_word)
        reshaped_sentence = rtl(self.current_sentence)
        # Ensure sentence appears on second line
        self.output_label.text = (
            f"{rtl('الحرف')}: {reshaped_letter}    {rtl('الكلمة')}: {reshaped_word}"
            "\n"
            f"{rtl('الجملة')}: {reshaped_sentence}"
        )

        # Update the KivyImage texture with the annotated frame
        buf = cv2.flip(display_frame, 0).tobytes()
        texture = Texture.create(
            size=(display_frame.shape[1], display_frame.shape[0]), colorfmt="bgr"
        )
        texture.blit_buffer(buf, colorfmt="bgr", bufferfmt="ubyte")
        self.img_widget.texture = texture

    def upload_image(self, instance):
        """
        Called by bottom-nav “صورة” (camera icon):
        - Stop any capture
        - Let user choose an image
        - Run a one-shot prediction on it
        """
        self.stop_camera()
        chooser = FileChooserIconView(filters=["*.jpg", "*.jpeg", "*.png"], size_hint=(1, 0.8))
        popup = ModalView(size_hint=(0.9, 0.9), background_color=(0.1, 0.1, 0.1, 1))
        chooser.bind(on_submit=lambda c, sel, t: self.process_uploaded_image(sel, popup))
        popup.add_widget(chooser)
        popup.open()

    def process_uploaded_image(self, selection, popup):
        popup.dismiss()
        if selection:
            img_path = selection[0]
            img = cv2.imread(img_path)
            if img is not None:
                self.predict_from_frame(img)

    def upload_video(self, instance):
        """
        Called by bottom-nav “فيديو” (video icon):
        - Stop any capture
        - Let user choose a video file
        - Begin continuous video playback + detection
        """
        self.stop_camera()
        chooser = FileChooserIconView(filters=["*.mp4", "*.avi", "*.mov"], size_hint=(1, 0.8))
        popup = ModalView(size_hint=(0.9, 0.9), background_color=(0.1, 0.1, 0.1, 1))
        chooser.bind(on_submit=lambda c, sel, t: self.process_uploaded_video(sel, popup))
        popup.add_widget(chooser)
        popup.open()

    def process_uploaded_video(self, selection, popup):
        popup.dismiss()
        if selection:
            video_path = selection[0]
            if os.path.exists(video_path):
                self.video_cap = cv2.VideoCapture(video_path)
                if not self.video_cap.isOpened():
                    self.video_cap = None
                    return
                self.is_video_mode = True
                self.event = Clock.schedule_interval(self.update, 1.0 / 30.0)

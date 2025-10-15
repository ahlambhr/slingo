import os
import json
import arabic_reshaper
import cv2
import numpy as np
import pytesseract
from bidi.algorithm import get_display
from datetime import datetime
from io import BytesIO
from pdf2image import convert_from_path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.text import LabelBase
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.graphics.texture import Texture
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.video import Video
from kivy.uix.gridlayout import GridLayout
from kivy.uix.camera import Camera
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.animation import Animation
from kivy.utils import get_color_from_hex

# ─── Register Arabic font & configure Tesseract ──────────────────────────────
LabelBase.register(name="Amiri", fn_regular="fonts/Amiri-Regular.ttf")
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"


def rtl(text: str) -> str:
    """Reshape Arabic text for right-to-left display."""
    return get_display(arabic_reshaper.reshape(text))


def clean_arabic_text(text: str) -> str:
    """Remove any non-Arabic characters except spaces and newlines."""
    if not isinstance(text, str):
        return ""
    return ''.join(c for c in text if 'ء' <= c <= 'ي' or c == ' ' or c == '\n')


class IconButton(ButtonBehavior, KivyImage):
    """A tappable Image button (for nav and other icons)."""
    pass


class ArabicInput(TextInput):
    """A TextInput subclass that preserves and reshapes Arabic as you type."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.original_text = ""

    def insert_text(self, substring, from_undo=False):
        self.original_text += substring
        reshaped_lines = [rtl(line) for line in self.original_text.splitlines()]
        self.text = "\n".join(reshaped_lines)

    def do_backspace(self, from_undo=False, mode='bkspc'):
        self.original_text = self.original_text[:-1]
        reshaped_lines = [rtl(line) for line in self.original_text.splitlines()]
        self.text = "\n".join(reshaped_lines)


# ─────────────────────────────────────────────────────────────────────────────────
#  TRANSLATOR SCREEN
# ─────────────────────────────────────────────────────────────────────────────────
class TranslatorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.font_name = "Amiri"
        self.history_file = "history.json"
        self.video_dataset_path = "datavideos"
        self.letter_sequence = []
        self.current_index = 0
        self.event = None
        self.current_mode = "text_to_sign"

        # ─────────────────────────────────────────────────────────────────────────────
        # PRE-INSTANTIATE ONE CAMERA (low resolution) FOR FAST OPEN/CLOSE
        # ─────────────────────────────────────────────────────────────────────────────
        self.kivy_cam = Camera(
            index=0,
            resolution=(800, 1200),  # lower res = faster startup
            play=False             # keep paused initially
        )

        # ─────────────────────────────────────────────────────────────────────────────
        # ROOT LAYOUT: Header / Back Button / Switch Bar / Middle / Bottom
        # ─────────────────────────────────────────────────────────────────────────────
        self.root_layout = BoxLayout(orientation='vertical')
        self.add_widget(self.root_layout)

        # ─────────────────────────────────────────────────────────────────────────────
        # 1) HEADER BAR: orange strip with “Slingo”
        # ─────────────────────────────────────────────────────────────────────────────
        header = BoxLayout(size_hint_y=None, height=70)
        with header.canvas.before:
            Color(1, 0.5, 0.1, 1)  # Bright orange
            self.header_rect = RoundedRectangle(
                pos=header.pos, size=header.size, radius=[0, 0, 0, 0]
            )
        header.bind(pos=lambda w, *_: setattr(self.header_rect, 'pos', w.pos))
        header.bind(size=lambda w, *_: setattr(self.header_rect, 'size', w.size))

        self.logo_label = Label(
            text="Slingo",
            font_name=self.font_name,
            font_size=44,
            bold=True,
            color=(0.03, 0.05, 0.15, 1),
            halign="left",
            valign="middle",
            size_hint=(1, 1),
            padding=(20, 0)
        )
        self.logo_label.bind(size=self.logo_label.setter('text_size'))
        header.add_widget(self.logo_label)
        self.root_layout.add_widget(header)

        # ─────────────────────────────────────────────────────────────────────────────
        # 2) “Back to Home” BUTTON (above the SWITCH BAR)
        # ─────────────────────────────────────────────────────────────────────────────
        self.back_btn = IconButton(
            source="assets/icons/angle-double-left.png",
            size_hint=(None, None),
            size=(50, 50),
            allow_stretch=True
        )
        back_anchor = AnchorLayout(size_hint_y=None, height=60, anchor_x='left', anchor_y='center')
        back_anchor.add_widget(self.back_btn)
        self.root_layout.add_widget(back_anchor)

        # ─────────────────────────────────────────────────────────────────────────────
        # 3) SWITCH BAR CARD: pill-shaped control (لغة ⇋ إشارة)
        # ─────────────────────────────────────────────────────────────────────────────
        switch_anchor = AnchorLayout(size_hint_y=None, height=90)
        switch_wrapper = BoxLayout(size_hint=(0.9, None), height=60)
        with switch_wrapper.canvas.before:
            # Drop-shadow behind pill
            Color(0, 0, 0, 0.18)
            self.switch_shadow = RoundedRectangle(
                pos=(switch_wrapper.x + 4, switch_wrapper.y - 4),
                size=(switch_wrapper.width, switch_wrapper.height),
                radius=[40, 40, 40, 40]
            )
            # White background for the switch pill
            Color(1, 1, 1, 1)
            self.switch_bg_card = RoundedRectangle(
                pos=switch_wrapper.pos,
                size=switch_wrapper.size,
                radius=[40, 40, 40, 40]
            )
        switch_wrapper.bind(pos=lambda w, *_: (
            setattr(self.switch_bg_card, 'pos', w.pos),
            setattr(self.switch_shadow, 'pos', (w.x + 4, w.y - 4))
        ))
        switch_wrapper.bind(size=lambda w, *_: (
            setattr(self.switch_bg_card, 'size', w.size),
            setattr(self.switch_shadow, 'size', w.size)
        ))

        switch_container = BoxLayout(
            orientation='horizontal', size_hint=(1, 1), padding=(4, 0), spacing=0
        )

        # 3.a) “لغة” button
        self.btn_language = Button(
            text=rtl("لغة"),
            font_name=self.font_name,
            font_size=26,
            bold=True,
            background_normal="",
            background_color=(1, 0.5, 0.0, 1),
            color=(0.93, 0.90, 0.97, 1),
            size_hint=(0.45, 1)
        )
        self.btn_language.bind(on_release=lambda *_: self._switch_to_language())

        # 3.b) custom switch icon
        self.btn_toggle = IconButton(
            source="assets/icons/switch.png",
            size_hint=(None, None),
            size=(50, 50),
            allow_stretch=True,
            keep_ratio=True,
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.btn_toggle.bind(on_release=lambda *_: self.toggle_mode())

        middle_holder = FloatLayout(size_hint=(0.10, 1))
        middle_holder.add_widget(self.btn_toggle)

        # 3.c) “إشارة” button
        self.btn_sign = Button(
            text=rtl("إشارة"),
            font_name=self.font_name,
            font_size=26,
            bold=True,
            background_normal="",
            background_color=(1, 1, 1, 1),
            color=(0.6, 0.6, 0.6, 1),
            size_hint=(0.45, 1)
        )
        self.btn_sign.bind(on_release=lambda *_: self._switch_to_sign())

        switch_container.add_widget(self.btn_language)
        switch_container.add_widget(middle_holder)
        switch_container.add_widget(self.btn_sign)
        switch_wrapper.add_widget(switch_container)
        switch_anchor.add_widget(switch_wrapper)
        self.root_layout.add_widget(switch_anchor)

        # ─────────────────────────────────────────────────────────────────────────────
        # 4) MIDDLE AREA: Video & Text Cards (with light-orange backgrounds)
        # ─────────────────────────────────────────────────────────────────────────────
        middle_container = BoxLayout(
            orientation='vertical',
            size_hint_y=1,
            spacing=4,
            padding=(0, 0, 0, 200)
        )
        self.root_layout.add_widget(middle_container)

        # 4.a) VIDEO CARD – light orange background, rounded corners, shadow
        avatar_anchor = AnchorLayout(size_hint_y=None, height=360)
        avatar_card = BoxLayout(size_hint=(0.9, None), height=340, padding=0)
        with avatar_card.canvas.before:
            Color(0, 0, 0, 0.18)  # Shadow
            self.video_shadow = RoundedRectangle(
                pos=(avatar_card.x + 5, avatar_card.y - 5),
                size=(avatar_card.width, avatar_card.height),
                radius=[40, 40, 40, 40]
            )
            Color(1, 0.9, 0.7, 1)  # Light orange
            self.video_bg = RoundedRectangle(
                pos=avatar_card.pos,
                size=avatar_card.size,
                radius=[40, 40, 40, 40]
            )
            Color(0.85, 0.85, 0.85, 1)  # Border
            self.video_border = RoundedRectangle(
                pos=(avatar_card.x + 2, avatar_card.y + 2),
                size=(avatar_card.width - 4, avatar_card.height - 4),
                radius=[40, 40, 40, 40]
            )
        avatar_card.bind(pos=lambda w, *_: (
            setattr(self.video_bg, 'pos', w.pos),
            setattr(self.video_shadow, 'pos', (w.x + 5, w.y - 5)),
            setattr(self.video_border, 'pos', (w.x + 2, w.y + 2))
        ))
        avatar_card.bind(size=lambda w, *_: (
            setattr(self.video_bg, 'size', w.size),
            setattr(self.video_shadow, 'size', w.size),
            setattr(self.video_border, 'size', (w.width - 4, w.height - 4))
        ))

        self.video_box = FloatLayout(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        self.video1 = Video(
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            allow_stretch=True,
            keep_ratio=False,
            state='stop',
            options={'eos': 'stop'}
        )
        self.video2 = Video(
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            allow_stretch=True,
            keep_ratio=False,
            state='stop',
            options={'eos': 'stop'}
        )
        self.video2.opacity = 0
        self.active_video = self.video1
        self.inactive_video = self.video2

        self.video_box.add_widget(self.video1)
        self.video_box.add_widget(self.video2)
        avatar_card.add_widget(self.video_box)
        avatar_anchor.add_widget(avatar_card)
        middle_container.add_widget(avatar_anchor)

        # 4.b) TEXT INPUT CARD – light orange background, rounded corners, shadow
        text_anchor = AnchorLayout(size_hint_y=None, height=480)
        text_input_card = BoxLayout(
            orientation='vertical',
            size_hint=(0.9, None),
            height=460,
            padding=(24, 24, 24, 24),
            spacing=8
        )
        with text_input_card.canvas.before:
            Color(0, 0, 0, 0.18)  # Shadow
            self.input_shadow = RoundedRectangle(
                pos=(text_input_card.x + 5, text_input_card.y - 5),
                size=(text_input_card.width, text_input_card.height),
                radius=[40, 40, 40, 40]
            )
            Color(1, 0.9, 0.7, 1)  # Light orange
            self.input_bg = RoundedRectangle(
                pos=text_input_card.pos,
                size=text_input_card.size,
                radius=[40, 40, 40, 40]
            )
            Color(0.85, 0.85, 0.85, 1)  # Border
            self.input_border = RoundedRectangle(
                pos=(text_input_card.x + 2, text_input_card.y + 2),
                size=(text_input_card.width - 4, text_input_card.height - 4),
                radius=[40, 40, 40, 40]
            )
        text_input_card.bind(pos=lambda w, *_: (
            setattr(self.input_bg, 'pos', w.pos),
            setattr(self.input_shadow, 'pos', (w.x + 5, w.y - 5)),
            setattr(self.input_border, 'pos', (w.x + 2, w.y + 2))
        ))
        text_input_card.bind(size=lambda w, *_: (
            setattr(self.input_bg, 'size', w.size),
            setattr(self.input_shadow, 'size', w.size),
            setattr(self.input_border, 'size', (w.width - 4, w.height - 4))
        ))

        self.input_label = Label(
            text=rtl("ادخل النص:"),  # “Enter text:”
            font_name=self.font_name,
            font_size=34,
            bold=True,
            color=(0.15, 0.15, 0.8, 1),
            size_hint_y=None,
            height=40,
            halign="right"
        )
        self.input_label.bind(size=self.input_label.setter('text_size'))

        self.text_input = ArabicInput(
            font_name="fonts/Amiri-Regular.ttf",
            font_size=30,
            halign="right",
            multiline=True,
            write_tab=False,
            background_color=(0, 0, 0, 0),
            foreground_color=(0.1, 0.1, 0.1, 1),
            cursor_color=(1, 0.4, 0, 1),
            padding=(12, 12),
            size_hint=(1, 1)
        )

        text_input_card.add_widget(self.input_label)
        text_input_card.add_widget(self.text_input)
        text_anchor.add_widget(text_input_card)
        middle_container.add_widget(text_anchor)

        # ─────────────────────────────────────────────────────────────────────────────
        # 5) BOTTOM NAVIGATION BAR: light orange + larger translate icon,
        #    thicker text, strong drop-shadow
        # ─────────────────────────────────────────────────────────────────────────────
        bottom_nav = BoxLayout(size_hint_y=None, height=120, spacing=0, padding=0)
        with bottom_nav.canvas.before:
            # Drop-shadow beneath navbar
            Color(0, 0, 0, 0.20)
            self.nav_shadow = RoundedRectangle(
                pos=(bottom_nav.x, bottom_nav.y - 8),
                size=(bottom_nav.width, bottom_nav.height + 8),
                radius=[40, 40, 0, 0]
            )
            # Light orange background (rounded top corners)
            Color(1, 0.9, 0.7, 1)
            self.nav_bg = RoundedRectangle(
                pos=bottom_nav.pos,
                size=bottom_nav.size,
                radius=[40, 40, 0, 0]
            )
        bottom_nav.bind(pos=lambda w, *_: (
            setattr(self.nav_bg, 'pos', w.pos),
            setattr(self.nav_shadow, 'pos', (w.x, w.y - 8))
        ))
        bottom_nav.bind(size=lambda w, *_: (
            setattr(self.nav_bg, 'size', w.size),
            setattr(self.nav_shadow, 'size', (w.width, w.height + 8))
        ))

        def _create_nav_item(icon_path, label_text, callback, is_translate=False):
            """
            Create a nav item (icon + label).
            If is_translate=True, the icon is larger so it stands out.
            """
            container = AnchorLayout(size_hint=(0.2, 1))
            box = BoxLayout(
                orientation='vertical',
                size_hint=(0.8, 1),
                pos_hint={'center_x': 0.5, 'center_y': 0.5},
                spacing=4
            )

            # If this is the Translate button, use a larger icon
            icon_size = (100, 100) if is_translate else (50, 50)
            icon_y_offset = 0.65 if is_translate else 0.6

            icon_btn = IconButton(
                source=icon_path,
                size_hint=(None, None),
                size=icon_size,
                pos_hint={'center_x': 0.5, 'center_y': icon_y_offset},
                allow_stretch=True
            )
            icon_btn.bind(on_release=lambda inst: callback())
            box.add_widget(icon_btn)

            lbl = Label(
                text=label_text,
                font_name=self.font_name,
                font_size=24,
                bold=True,
                color=(0.15, 0.15, 0.15, 1),
                size_hint_y=None,
                height=32,
                halign="center"
            )
            lbl.bind(size=lbl.setter('text_size'))
            box.add_widget(lbl)

            container.add_widget(box)
            return container

        chat_item = _create_nav_item(
            icon_path="assets/icons/mic.png",
            label_text="Chat",
            callback=self.recognize_speech,
            is_translate=False
        )
        camera_item = _create_nav_item(
            icon_path="assets/icons/camera.png",
            label_text="Camera",
            callback=self.open_camera_modal,
            is_translate=False
        )
        translate_item = _create_nav_item(
            icon_path="assets/icons/translate.png",
            label_text="Translate",
            callback=lambda: self.start_translation(None),
            is_translate=True
        )
        history_item = _create_nav_item(
            icon_path="assets/icons/history.png",
            label_text="History",
            callback=self.show_history,
            is_translate=False
        )
        pdf_item = _create_nav_item(
            icon_path="assets/icons/pdf.png",
            label_text="PDF",
            callback=self.select_pdf_as_image,
            is_translate=False
        )

        for item in (chat_item, camera_item, translate_item, history_item, pdf_item):
            bottom_nav.add_widget(item)

        self.root_layout.add_widget(bottom_nav)

        # Ensure the history file exists
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    # ─────────────────────────────────────────────────────────────────────────────
    # Bind "Back to Home" button once this screen is in a ScreenManager
    # ─────────────────────────────────────────────────────────────────────────────
    def on_parent(self, instance, parent):
        """
        Called when this screen is added to the ScreenManager.
        Bind back_btn to switch back to "home" (instead of "translator").
        """
        if parent:
            self.back_btn.bind(on_release=lambda *_: setattr(parent, 'current', "home"))

    # ─────────────────────────────────────────────────────────────────────────────
    # MODE SWITCH HELPERS (Language ↔ Sign)
    # ─────────────────────────────────────────────────────────────────────────────
    def _switch_to_language(self):
        self.current_mode = "text_to_sign"
        self.btn_language.background_color = (1, 0.5, 0.0, 1)
        self.btn_language.color = (0.93, 0.90, 0.97, 1)
        self.btn_sign.background_color = (1, 1, 1, 1)
        self.btn_sign.color = (0.6, 0.6, 0.6, 1)

    def _switch_to_sign(self):
        self.current_mode = "sign_to_text"
        self.btn_sign.background_color = (1, 0.5, 0.0, 1)
        self.btn_sign.color = (0.93, 0.90, 0.97, 1)
        self.btn_language.background_color = (1, 1, 1, 1)
        self.btn_language.color = (0.6, 0.6, 0.6, 1)
        if self.manager:
            self.manager.current = "predictor"

    def toggle_mode(self):
        if self.current_mode == "text_to_sign":
            self._switch_to_sign()
        else:
            self._switch_to_language()

    # ─────────────────────────────────────────────────────────────────────────────
    # OPEN CAMERA MODAL: reuse preloaded Camera for speed
    # ─────────────────────────────────────────────────────────────────────────────
    def open_camera_modal(self):
        """
        Opens a ModalView containing:
        1. A top-right red “X” to close.
        2. The pre-instantiated Camera widget (play=True now).
        3. A modern bottom bar with:
           - A white circular camera‐snap button.
           - A rounded‐corner blue “Extract picture from file” button
             with a small picture icon on its left.
        """
        # Make sure the camera is playing
        self.kivy_cam.play = True

        # If the camera already has a parent, remove it so we can re-add
        if self.kivy_cam.parent:
            self.kivy_cam.parent.remove_widget(self.kivy_cam)

        # Full-screen dark background
        self.camera_modal = ModalView(size_hint=(0.9, 0.9), background_color=(0.1, 0.1, 0.1, 1))
        root = BoxLayout(orientation='vertical', spacing=10, padding=10)

        # ─────────────────────────────────────────────────────────────────────────
        # Top bar with close button (X)
        # ─────────────────────────────────────────────────────────────────────────
        top_bar = BoxLayout(size_hint_y=None, height=40)
        top_bar.add_widget(Label(size_hint_x=0.9))
        close_btn = Button(
            text="X",
            size_hint=(None, None),
            size=(40, 40),
            background_normal="",
            background_color=(0.8, 0.1, 0.1, 1),  # red
            color=(1, 1, 1, 1),
            font_size=20,
            bold=True
        )
        close_btn.bind(on_release=self._close_camera_modal)
        top_bar.add_widget(close_btn)
        root.add_widget(top_bar)

        # ─────────────────────────────────────────────────────────────────────────
        # Reuse the preloaded Camera widget
        # ─────────────────────────────────────────────────────────────────────────
        root.add_widget(self.kivy_cam)

        # ─────────────────────────────────────────────────────────────────────────
        # Bottom bar (centered modern layout)
        # ─────────────────────────────────────────────────────────────────────────
        bottom_bar = AnchorLayout(size_hint_y=None, height=100)

        btn_layout = BoxLayout(
            orientation='horizontal',
            size_hint=(0.8, None),
            height=60,
            spacing=30,
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        # ─── CAMERA BUTTON ───────────────────────────────────────────────────────
        camera_wrap = FloatLayout(size_hint=(None, None), size=(60, 60))
        with camera_wrap.canvas.before:
            Color(1, 1, 1, 1)  # white circle
            br_cam = RoundedRectangle(
                pos=camera_wrap.pos,
                size=camera_wrap.size,
                radius=[30, 30, 30, 30]
            )
        camera_wrap.bind(pos=lambda w, *_: setattr(br_cam, 'pos', w.pos))
        camera_wrap.bind(size=lambda w, *_: setattr(br_cam, 'size', w.size))

        camera_btn = IconButton(
            source="assets/icons/camera.png",
            size_hint=(None, None),
            size=(32, 32),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            allow_stretch=True
        )
        camera_btn.bind(on_release=lambda inst: self._capture_from_camera())
        camera_wrap.add_widget(camera_btn)

        # ─── EXTRACT‐FROM‐FILE BUTTON ────────────────────────────────────────────
        extract_wrap = BoxLayout(
            orientation='horizontal',
            size_hint=(None, None),
            size=(240, 60),
            spacing=10
        )
        # Rounded‐corner blue background
        with extract_wrap.canvas.before:
            Color(0.2, 0.6, 0.9, 1)  # blue
            br_ext = RoundedRectangle(
                pos=extract_wrap.pos,
                size=extract_wrap.size,
                radius=[20, 20, 20, 20]
            )
        extract_wrap.bind(pos=lambda w, *_: setattr(br_ext, 'pos', w.pos))
        extract_wrap.bind(size=lambda w, *_: setattr(br_ext, 'size', w.size))

        pic_icon = IconButton(
            source="assets/icons/picture.png",
            size_hint=(None, None),
            size=(24, 24),
            pos_hint={'center_y': 0.5},
            allow_stretch=True
        )
        pic_icon.bind(on_release=lambda inst: (
            self._close_camera_modal(),
            self.select_image_from_file()
        ))

        extract_label = Button(
            text="Extract picture from file",
            font_name=self.font_name,
            font_size=16,
            bold=True,
            size_hint=(None, None),
            size=(180, 60),
            background_normal="",
            background_color=(0, 0, 0, 0),  # transparent so blue shows through
            color=(1, 1, 1, 1),
            halign="left",
            valign="middle",
            padding=(10, 0)
        )
        extract_label.bind(on_release=lambda inst: (
            self._close_camera_modal(),
            self.select_image_from_file()
        ))

        extract_wrap.add_widget(pic_icon)
        extract_wrap.add_widget(extract_label)

        btn_layout.add_widget(camera_wrap)
        btn_layout.add_widget(extract_wrap)
        bottom_bar.add_widget(btn_layout)
        root.add_widget(bottom_bar)

        self.camera_modal.add_widget(root)
        self.camera_modal.open()

    def _close_camera_modal(self, *args):
        # Pause the camera so it doesn’t keep running in background
        self.kivy_cam.play = False
        self.camera_modal.dismiss()

    # ─────────────────────────────────────────────────────────────────────────────
    # CAPTURE PHOTO FROM CAMERA: save a temp PNG, then ROI+OCR
    # ─────────────────────────────────────────────────────────────────────────────
    def _capture_from_camera(self):
        """
        Export the current frame from Kivy Camera as a PNG (“temp_capture.png”),
        then read it with cv2 and let user select ROI for OCR.
        """
        temp_path = "temp_capture.png"
        self.kivy_cam.export_to_png(temp_path)

        img = cv2.imdecode(np.fromfile(temp_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return

        r = cv2.selectROI("حدد المنطقة", img, fromCenter=False, showCrosshair=True)
        cv2.destroyAllWindows()
        if r == (0, 0, 0, 0):
            return

        x, y, w, h = r
        roi = img[int(y):int(y+h), int(x):int(x+h)]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray, lang='ara')
        cleaned = ''.join(c for c in text if 'ء' <= c <= 'ي' or c == ' ')
        self.text_input.original_text = cleaned
        self.text_input.text = rtl(cleaned)

        self._close_camera_modal()

    # ─────────────────────────────────────────────────────────────────────────────
    # select_image_from_file: pick image, preview, then ROI+OCR
    # ─────────────────────────────────────────────────────────────────────────────
    def select_image_from_file(self):
        filechooser = FileChooserIconView(filters=['*.png', '*.jpg', '*.jpeg'], size_hint=(1, 0.7))
        image_preview = KivyImage(size_hint=(1, 0.5))
        confirm_button = Button(
            text="Extract picture from file",  # English text
            size_hint=(1, 0.1),
            font_name=self.font_name,
            font_size=20,
            background_color=(0.2, 0.6, 0.9, 1),  # same blue
            color=(1, 1, 1, 1)
        )
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(filechooser)
        layout.add_widget(image_preview)
        layout.add_widget(confirm_button)
        popup = ModalView(size_hint=(0.95, 0.95), background_color=(0.1, 0.1, 0.1, 1))
        popup.add_widget(layout)

        selected = {"path": None}

        def on_select(_, selection):
            if selection:
                path = selection[0]
                selected["path"] = path
                img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is not None:
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    img_rgb = cv2.resize(img_rgb, (800, 600))
                    img_rgb = cv2.flip(img_rgb, 0)
                    texture = Texture.create(size=(img_rgb.shape[1], img_rgb.shape[0]), colorfmt='rgb')
                    texture.blit_buffer(img_rgb.flatten(), colorfmt='rgb', bufferfmt='ubyte')
                    image_preview.texture = texture

        filechooser.bind(selection=on_select)

        def on_confirm(_):
            path = selected["path"]
            if not path:
                return
            popup.dismiss()
            img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                return
            r = cv2.selectROI("حدد المنطقة", img, fromCenter=False, showCrosshair=True)
            cv2.destroyAllWindows()
            if r == (0, 0, 0, 0):
                return
            x, y, w, h = r
            roi = img[int(y):int(y+h), int(x):int(x+h)]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray, lang='ara')
            cleaned = ''.join(c for c in text if 'ء' <= c <= 'ي' or c == ' ')
            self.text_input.original_text = cleaned
            self.text_input.text = rtl(cleaned)

        confirm_button.bind(on_release=on_confirm)
        popup.open()

    # ─────────────────────────────────────────────────────────────────────────────
    # UPDATED start_translation: warn if any non-Arabic chars
    # ─────────────────────────────────────────────────────────────────────────────
    def start_translation(self, instance):
        raw_text = getattr(self.text_input, 'original_text', "").strip()
        if not raw_text:
            return

        import re
        if re.search(r"[^\sء-ي]", raw_text):
            content = BoxLayout(orientation='vertical', spacing=10, padding=20)
            warning_label = Label(
                text=rtl("النص يحتوي على أحرف غير عربية. هل تريد المتابعة؟"),
                font_name=self.font_name,
                font_size=28,
                color=(0.9, 0.1, 0.1, 1),
                halign="center",
                valign="middle"
            )
            warning_label.bind(size=warning_label.setter('text_size'))
            btn_layout = BoxLayout(size_hint_y=None, height=60, spacing=20)

            btn_continue = Button(
                text=rtl("متابعة"),
                font_name=self.font_name,
                font_size=24,
                bold=True,
                background_color=(0.1, 0.5, 0.1, 1),
                color=(1, 1, 1, 1)
            )
            btn_cancel = Button(
                text=rtl("إلغاء"),
                font_name=self.font_name,
                font_size=24,
                bold=True,
                background_color=(0.5, 0.1, 0.1, 1),
                color=(1, 1, 1, 1)
            )

            btn_layout.add_widget(btn_continue)
            btn_layout.add_widget(btn_cancel)
            content.add_widget(warning_label)
            content.add_widget(btn_layout)

            popup = Popup(
                title=rtl("تحذير"),
                content=content,
                size_hint=(0.8, 0.4),
                title_font=self.font_name
            )

            btn_continue.bind(on_release=lambda _: (
                popup.dismiss(),
                self._really_start_translation(raw_text)
            ))
            btn_cancel.bind(on_release=lambda _: popup.dismiss())

            popup.open()
        else:
            self._really_start_translation(raw_text)

    def _really_start_translation(self, cleaned_text):
        text = clean_arabic_text(cleaned_text)
        self.save_history(text)
        self.letter_sequence = [c for c in text if c != '\n']
        self.current_index = 0
        if self.event:
            self.event.cancel()
        self.event = Clock.schedule_interval(self.show_next_letter, 1.0)

    # ─────────────────────────────────────────────────────────────────────────────
    # show_next_letter & display_video: unchanged
    # ─────────────────────────────────────────────────────────────────────────────
    def show_next_letter(self, dt):
        if self.current_index >= len(self.letter_sequence):
            if self.event:
                self.event.cancel()
            return
        letter = self.letter_sequence[self.current_index]
        if letter == ' ':
            self.current_index += 1
            return
        vids = [
            f for f in os.listdir(self.video_dataset_path)
            if f.startswith(letter) and f.lower().endswith(('.mp4','.avi','.mov'))
        ]
        if vids:
            video_path = os.path.join(self.video_dataset_path, vids[0])
            self.display_video(video_path)
        self.current_index += 1

    def display_video(self, path):
        self.inactive_video.source = path
        self.inactive_video.opacity = 0
        self.inactive_video.state = 'play'

        def check_loaded(dt):
            if self.inactive_video.texture:
                self.video_box.remove_widget(self.inactive_video)
                self.video_box.add_widget(self.inactive_video)
                self.active_video.opacity = 0
                self.inactive_video.opacity = 1
                self.active_video.state = 'stop'
                self.active_video, self.inactive_video = self.inactive_video, self.active_video
            else:
                Clock.schedule_once(check_loaded, 0.1)

        Clock.schedule_once(check_loaded, 0.1)

    # ─────────────────────────────────────────────────────────────────────────────
    # HISTORY POPUP: plain rows with transparent text button + trash icon
    # ─────────────────────────────────────────────────────────────────────────────
    def show_history(self):
        if not os.path.exists(self.history_file):
            return

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                all_history = json.load(f)
        except:
            all_history = []

        if not all_history:
            return

        # Take the last 10 entries and reverse so newest is on top
        last_ten = all_history[-10:]
        display_list = list(reversed(last_ten))

        # Vertical GridLayout to hold up to 10 rows
        layout = GridLayout(
            cols=1,
            spacing=5,
            padding=10,
            size_hint_y=None
        )
        layout.bind(minimum_height=layout.setter('height'))

        for idx, entry in enumerate(display_list):
            full_index = len(all_history) - 1 - idx
            full_text = entry['text']
            timestamp = entry['time']

            # Truncate preview to first 5 words + "..." if longer
            words = full_text.split()
            if len(words) > 5:
                preview = " ".join(words[:5]) + "..."
            else:
                preview = full_text

            # Build a simple RTL string: preview on the right, timestamp on the left
            display_text = rtl(f"{preview} : {timestamp}")

            # Each row: [ preview_button (80%) | trash_icon (20%) ]
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=60)

            # 1) Plain, transparent button for the preview text
            text_btn = Button(
                text=display_text,
                font_name=self.font_name,
                font_size=22,
                bold=True,
                color=(1, 1, 1, 1),           # white text
                background_color=(0, 0, 0, 0),  # fully transparent
                halign='right',
                valign='middle',
                size_hint=(0.8, 1)
            )
            text_btn.bind(size=lambda w, *_: setattr(w, 'text_size', (w.width - 20, None)))
            text_btn.text_size = (text_btn.width - 20, None)

            # On tap, load the full text back into the translator
            text_btn.bind(on_release=lambda btn, t=full_text: self.load_from_history(t))

            row.add_widget(text_btn)

            # 2) Trash icon button on the right, no colored background
            trash_container = AnchorLayout(
                size_hint=(0.2, 1),
                anchor_x='center',
                anchor_y='center'
            )
            trash_btn = IconButton(
                source="assets/icons/trash.png",
                size_hint=(None, None),
                size=(30, 30),
                pos_hint={'center_x': 0.5, 'center_y': 0.5},
                allow_stretch=True
            )
            trash_btn.bind(on_release=lambda inst, i=full_index: self.delete_history(i))
            trash_container.add_widget(trash_btn)

            row.add_widget(trash_container)
            layout.add_widget(row)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(layout)

        if hasattr(self, 'history_popup') and self.history_popup:
            self.history_popup.dismiss()

        popup = Popup(
            title=rtl("🕘 سجل الترجمات"),  # “Translation History”
            content=scroll,
            title_font=self.font_name,
            size_hint=(0.95, 0.9)
        )
        popup.open()
        self.history_popup = popup

    def delete_history(self, index: int):
        if not os.path.exists(self.history_file):
            return
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []

        if 0 <= index < len(history):
            del history[index]
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)

        if hasattr(self, 'history_popup') and self.history_popup:
            self.history_popup.dismiss()
        self.show_history()

    def load_from_history(self, text: str):
        self.text_input.original_text = text
        self.text_input.text = rtl(text)
        if hasattr(self, 'history_popup'):
            self.history_popup.dismiss()

    # ─────────────────────────────────────────────────────────────────────────────
    # SAVE_HISTORY: appends to history.json
    # ─────────────────────────────────────────────────────────────────────────────
    def save_history(self, text: str):
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []
        history.append({"time": datetime.now().strftime("%Y-%m-%d %H:%M"), "text": text})
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    # ─────────────────────────────────────────────────────────────────────────────
    # select_pdf_as_image & extract_text: unchanged from before
    # ─────────────────────────────────────────────────────────────────────────────
    def select_pdf_as_image(self):
        filechooser = FileChooserIconView(filters=['*.pdf'], size_hint=(1, 0.8))
        confirm_button = Button(
            text=rtl("✅ تحميل صفحات PDF"),
            size_hint=(1, 0.1),
            font_name=self.font_name,
            font_size=20
        )
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(filechooser)
        layout.add_widget(confirm_button)
        popup = ModalView(size_hint=(0.95, 0.95))
        popup.add_widget(layout)

        selected = {"path": None}

        def on_select(_, selection):
            if selection:
                selected["path"] = selection[0]

        def on_confirm(_):
            popup.dismiss()
            if not selected["path"]:
                return
            try:
                images = convert_from_path(selected["path"], dpi=60)
                scroll_layout = GridLayout(cols=1, spacing=10, padding=10, size_hint_y=None)
                scroll_layout.bind(minimum_height=scroll_layout.setter('height'))
                for idx, img in enumerate(images):
                    buf = BytesIO()
                    img.save(buf, format='PNG')
                    buf.seek(0)
                    core_img = CoreImage(buf, ext='png').texture
                    img_widget = KivyImage(texture=core_img, size_hint_y=None, height=360)
                    btn = Button(
                        text=rtl(f"اختر نص الصفحة {idx+1}"),
                        font_name=self.font_name,
                        font_size=20,
                        size_hint_y=None,
                        height=64
                    )
                    def make_callback(img_np):
                        def callback(instance):
                            self.extract_text_from_selected_image(img_np)
                        return callback
                    img_np = np.array(img)
                    btn.bind(on_release=make_callback(img_np))
                    scroll_layout.add_widget(img_widget)
                    scroll_layout.add_widget(btn)

                scroll_view = ScrollView(size_hint=(1, 1))
                scroll_view.add_widget(scroll_layout)
                pdf_popup = ModalView(size_hint=(0.98, 0.98))
                pdf_popup.add_widget(scroll_view)
                pdf_popup.open()
            except Exception:
                pass

        filechooser.bind(selection=on_select)
        confirm_button.bind(on_release=on_confirm)
        popup.open()

    def extract_text_from_selected_image(self, img_np):
        try:
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            r = cv2.selectROI("حدد المنطقة", img_bgr, fromCenter=False, showCrosshair=True)
            cv2.destroyAllWindows()
            if r == (0, 0, 0, 0):
                return
            x, y, w, h = r
            roi = img_bgr[int(y):int(y+h), int(x):int(x+h)]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray, lang='ara')
            cleaned = ''.join(c for c in text if 'ء' <= c <= 'ي' or c == ' ')
            self.text_input.original_text = cleaned
            self.text_input.text = rtl(cleaned)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────────
    # recognize_speech: unchanged from before
    # ─────────────────────────────────────────────────────────────────────────────
    def recognize_speech(self):
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                audio = recognizer.listen(source, timeout=5)
                text = recognizer.recognize_google(audio, language='ar-SA')
                self.text_input.original_text = text
                self.text_input.text = rtl(text)
        except:
            pass


# ─────────────────────────────────────────────────────────────────────────────────
#  PREDICTOR SCREEN (unchanged except binding “back to translator”)
# ─────────────────────────────────────────────────────────────────────────────────
class PredictorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 1) “Back to Home” button at top-left (bound via on_parent)
        self.back_btn = IconButton(
            source="assets/icons/angle-double-left.png",
            size_hint=(None, None),
            size=(50, 50),
            allow_stretch=True
        )
        self.add_widget(self.back_btn)

        # 2) A simple label for Predictor mode (centered)
        lbl = Label(
            text=rtl("صفحة التعرُّف على الإشارة"),
            font_name="Amiri",
            font_size=30,
            bold=True,
            halign="center",
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        lbl.bind(size=lbl.setter('text_size'))
        self.add_widget(lbl)

    def on_parent(self, instance, parent):
        """
        Bind the back button as soon as this screen is added to its ScreenManager.
        Pressing back goes back to the Translator screen.
        """
        if parent:
            self.back_btn.bind(on_release=lambda *_: setattr(parent, 'current', "translator"))


# ─────────────────────────────────────────────────────────────────────────────────
#  SLINGO APP (SCREENMANAGER → adds Home, Translator, Predictor)
# ─────────────────────────────────────────────────────────────────────────────────
class SlingoApp(App):
    def build(self):
        sm = ScreenManager()

        # — First, add your HomeScreen (must be defined somewhere else) —
        #    We assume you have something like `from screens.home import HomeScreen`
        from screens.home import HomeScreen
        sm.add_widget(HomeScreen(name="home"))

        # — Then add Translator and Predictor Screens —
        sm.add_widget(TranslatorScreen(name="translator"))
        sm.add_widget(PredictorScreen(name="predictor"))

        # Start on the Home screen:
        sm.current = "home"
        return sm


if __name__ == "__main__":
    SlingoApp().run()

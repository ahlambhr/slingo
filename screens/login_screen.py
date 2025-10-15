from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.core.text import LabelBase
from kivy.utils import get_color_from_hex
from kivy.app import App

import arabic_reshaper
from bidi.algorithm import get_display
import json
import os

LabelBase.register(name="Amiri", fn_regular="fonts/Amiri-Regular.ttf")
Window.clearcolor = (1, 1, 1, 1)

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def rtl(text):
    return get_display(arabic_reshaper.reshape(text))


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Background image
        with self.canvas.before:
            self.bg = Rectangle(source="assets/login_bg.png", size=self.size, pos=self.pos)
        self.bind(size=self.update_bg, pos=self.update_bg)

        container = FloatLayout()

        # Glass card
        card = BoxLayout(orientation='vertical', spacing=20, padding=30,
                         size_hint=(None, None), size=(700, 600), pos_hint={"center_x": 0.5, "center_y": 0.5})

        with card.canvas.before:
            Color(1, 1, 1, 0.12)  # light glass effect
            self.card_bg = RoundedRectangle(radius=[35], pos=card.pos, size=card.size)
        card.bind(pos=self.update_card, size=self.update_card)

        # Fade-in animation
        self.opacity = 0
        Animation(opacity=1, d=0.6).start(self)

        # Profile icon
        profile = Image(source="assets/user.png", size_hint=(None, None), size=(80, 80), allow_stretch=True)
        profile.pos_hint = {"center_x": 0.5}

        # Title
        title = Label(text=rtl("تسجيل الدخول"), font_name="Amiri", font_size=35,
                      color=[0, 0, 0, 1], size_hint=(1, None), height=30, halign="center")

        # Username and password
        self.username = self.create_input("assets/user.png", "اسم المستخدم")
        self.password = self.create_input("assets/lock.png", "كلمة المرور", password=True)

        # Login button
        self.login_btn = Button(
            text=rtl("تسجيل الدخول"),
            font_name="Amiri",
            font_size=28,
            size_hint=(1, None),
            height=60,
            background_normal='',
            background_color=(1, 0.4, 0.2, 1),
            color=(1, 1, 1, 1)
        )
        with self.login_btn.canvas.before:
            Color(1, 0.4, 0.2, 1)
            self.btn_bg = RoundedRectangle(radius=[24], pos=self.login_btn.pos, size=self.login_btn.size)
        self.login_btn.bind(pos=self.update_btn, size=self.update_btn)
        self.login_btn.bind(on_press=self.login)

        # Warning label
        self.warning_label = Label(
            text="",
            font_name="Amiri",
            font_size=18,
            color=[1, 0, 0, 1],
            size_hint=(1, None),
            height=20,
            halign="center"
        )

        # Register prompt
        self.register_label = Button(
            text=rtl("لا تملك حسابًا؟ سجل الآن"),
            font_name="Amiri",
            font_size=26,
            background_normal="",
            background_color=(0, 0, 0, 0),
            color=(0.1, 0.1, 0.1, 1),
            size_hint=(1, None),
            height=30
        )
        self.register_label.bind(on_press=lambda x: setattr(self.manager, 'current', 'register'))

        # Add widgets
        card.add_widget(profile)
        card.add_widget(title)
        card.add_widget(self.username)
        card.add_widget(self.password)
        card.add_widget(self.login_btn)
        card.add_widget(self.warning_label)
        card.add_widget(self.register_label)

        container.add_widget(card)
        self.add_widget(container)

    def create_input(self, icon_path, hint, password=False):
        layout = BoxLayout(orientation="horizontal", size_hint=(1, None), height=50, spacing=10)
        img = Image(source=icon_path, size_hint=(None, None), size=(28, 28))

        txt = TextInput(
            hint_text=rtl(hint),
            font_name="Amiri",
            font_size=20,
            halign="right",
            multiline=False,
            password=password,
            foreground_color=(0, 0, 0, 1),
            background_color=(0, 0, 0, 0),
            background_normal='',
            padding=(10, 10),
            size_hint=(1, 1)
        )

        layout.add_widget(img)
        layout.add_widget(txt)
        layout.text_input = txt

        # Underline
        with layout.canvas.after:
            Color(1, 0.4, 0, 1)
            layout.underline = Rectangle(size=(0, 2), pos=(0, 0))

        def update_line(*args):
            layout.underline.size = (layout.width, 2)
            layout.underline.pos = (layout.x, layout.y)
        layout.bind(pos=update_line, size=update_line)

        return layout

    def login(self, instance):
        uname = self.username.text_input.text.strip()
        pwd = self.password.text_input.text.strip()
        users = load_users()

        self.username.text_input.hint_text = rtl("اسم المستخدم")
        self.username.text_input.hint_text_color = (0.5, 0.5, 0.5, 1)
        self.password.text_input.hint_text = rtl("كلمة المرور")
        self.password.text_input.hint_text_color = (0.5, 0.5, 0.5, 1)
        self.warning_label.text = ""

        if not uname:
            self.username.text_input.hint_text = rtl("⚠️ أدخل اسم المستخدم")
            self.username.text_input.hint_text_color = [1, 0, 0, 1]
            return
        if not pwd:
            self.password.text_input.hint_text = rtl("⚠️ أدخل كلمة المرور")
            self.password.text_input.hint_text_color = [1, 0, 0, 1]
            return
        # 1) If admin credentials, go to Dashboard
        if uname == "admin_ahlam" and pwd == "admin1234":
            App.get_running_app().current_user = "admin_ahlam"
            self.warning_label.text = ""
            self.manager.current = "admin_dashboard"
            return

        if uname in users and users[uname]["password"] == pwd:
            App.get_running_app().current_user = uname
            self.manager.current = "home"
        else:
            self.warning_label.text = rtl("⚠️ اسم المستخدم أو كلمة المرور غير صحيحة")

    def update_bg(self, *args):
        self.bg.size = self.size
        self.bg.pos = self.pos

    def update_card(self, instance, *args):
        self.card_bg.pos = instance.pos
        self.card_bg.size = instance.size

    def update_btn(self, instance, *args):
        self.btn_bg.pos = instance.pos
        self.btn_bg.size = instance.size

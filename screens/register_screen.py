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
from kivy.app import App
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

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f)

def rtl(text):
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(text))

class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            self.bg = Rectangle(source="assets/register_bg.png", size=self.size, pos=self.pos)
        self.bind(size=self.update_bg, pos=self.update_bg)

        container = FloatLayout()

        card = BoxLayout(orientation='vertical', spacing=20, padding=30,
                         size_hint=(None, None), size=(700, 600), pos_hint={"center_x": 0.5, "center_y": 0.5})

        with card.canvas.before:
            Color(1, 1, 1, 0.12)
            self.card_bg = RoundedRectangle(radius=[35], pos=card.pos, size=card.size)
        card.bind(pos=self.update_card, size=self.update_card)

        self.opacity = 0
        Animation(opacity=1, d=0.6).start(self)

        profile = Image(source="assets/user.png", size_hint=(None, None), size=(80, 80))
        profile.pos_hint = {"center_x": 0.5}

        title = Label(text=rtl("إنشاء حساب جديد"), font_name="Amiri", font_size=28,
                      color=[0, 0, 0, 1], size_hint=(1, None), height=30, halign="center")

        self.username = self.create_input("assets/user.png", "اسم المستخدم")
        self.password = self.create_input("assets/lock.png", "كلمة المرور", password=True)
        self.confirm_password = self.create_input("assets/lock.png", "تأكيد كلمة المرور", password=True)

        self.message = Label(text="", font_name="Amiri", font_size=16, color=[1, 0, 0, 1],
                             size_hint=(1, None), height=20, halign="center")

        self.register_btn = Button(text=rtl("تسجيل"), font_name="Amiri", font_size=28,
                                   size_hint=(1, None), height=50,
                                   background_normal='', background_color=(1, 0.4, 0.2, 1), color=(1, 1, 1, 1))
        with self.register_btn.canvas.before:
            Color(1, 0.4, 0.2, 1)
            self.btn_bg = RoundedRectangle(radius=[24], pos=self.register_btn.pos, size=self.register_btn.size)
        self.register_btn.bind(pos=self.update_btn, size=self.update_btn)
        self.register_btn.bind(on_press=self.register)

        back_btn = Button(text=rtl("🔙 العودة لتسجيل الدخول"), font_name="Amiri", font_size=26,
                          background_normal='', background_color=(0, 0, 0, 0), color=(0.2, 0.2, 0.2, 1),
                          size_hint=(1, None), height=30)
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'login'))

        card.add_widget(profile)
        card.add_widget(title)
        card.add_widget(self.username)
        card.add_widget(self.password)
        card.add_widget(self.confirm_password)
        card.add_widget(self.register_btn)
        card.add_widget(self.message)
        card.add_widget(back_btn)

        container.add_widget(card)
        self.add_widget(container)

    def create_input(self, icon_path, hint, password=False):
        layout = BoxLayout(orientation="horizontal", size_hint=(1, None), height=60, spacing=10)
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

        with layout.canvas.after:
            Color(1, 0.4, 0, 1)
            layout.underline = Rectangle(size=(0, 2), pos=(0, 0))

        def update_line(*args):
            layout.underline.size = (layout.width, 2)
            layout.underline.pos = (layout.x, layout.y)
        layout.bind(pos=update_line, size=update_line)

        return layout

    def register(self, instance):
        users = load_users()
        uname = self.username.text_input.text.strip()
        pwd = self.password.text_input.text.strip()
        confirm_pwd = self.confirm_password.text_input.text.strip()

        if uname in users:
            self.message.text = rtl("❗ اسم المستخدم موجود مسبقًا")
        elif not uname or not pwd or not confirm_pwd:
            self.message.text = rtl("⚠️ يرجى ملء جميع الحقول")
        elif pwd != confirm_pwd:
            self.message.text = rtl("❌ كلمتا المرور غير متطابقتين")
        else:
            users[uname] = {"password": pwd}
            save_users(users)
            App.get_running_app().current_user = uname
            self.manager.current = "home"

    def update_bg(self, *args):
        self.bg.size = self.size
        self.bg.pos = self.pos

    def update_card(self, instance, *args):
        self.card_bg.pos = instance.pos
        self.card_bg.size = instance.size

    def update_btn(self, instance, *args):
        self.btn_bg.pos = instance.pos
        self.btn_bg.size = instance.size

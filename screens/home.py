import json
import os
import random
import tempfile
import subprocess
import webbrowser

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.carousel import Carousel
from kivy.uix.modalview import ModalView
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, RoundedRectangle
from kivy.graphics.texture import Texture

import arabic_reshaper
from bidi.algorithm import get_display

# Register Arabic font & white background
LabelBase.register(name="Amiri", fn_regular="fonts/Amiri-Regular.ttf")
Window.clearcolor = (1, 1, 1, 1)

def rtl(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))

class IconButton(ButtonBehavior, KivyImage):
    pass

class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # tighten spacing so sections sit closer
        self.layout = BoxLayout(orientation='vertical', spacing=12, padding=24)
        self.add_widget(self.layout)
        self.daily_sign = self.load_random_daily_sign()

    def on_pre_enter(self):
        # pick a brand-new random sign (with its image) every time HomeScreen is shown
        self.daily_sign = self.load_random_daily_sign()

        self.layout.clear_widgets()
        username = getattr(App.get_running_app(), 'current_user', 'User')

        # 1) Top bar with Logout
        top = BoxLayout(orientation='horizontal', size_hint_y=0.08, spacing=12)
        # Logout button
        logout_btn = Button(
            text=rtl("تسجيل خروج"),
            font_name="Amiri", font_size=20,
            size_hint=(None, 1), width=120,
            background_normal="", background_color=(1, 0.5, 0.1, 1)
        )
        def logout(inst):
            App.get_running_app().current_user = None
            self.manager.current = 'login'
        logout_btn.bind(on_release=logout)
        top.add_widget(logout_btn)

        # Greeting and profile image
        greeting = Label(
            text=rtl(f"مرحباً، {username}"),
            font_name="Amiri", font_size=28, bold=True,
            halign='right', valign='middle', color=(0.1,0.1,0.1,1)
        )
        greeting.bind(size=greeting.setter('text_size'))
        profile = KivyImage(source="assets/circle-user.png", size_hint=(None,1), width=44)
        top.add_widget(greeting)
        top.add_widget(profile)

        # 2) Lingo banner (30% weight)
        lingo_banner = KivyImage(
            source="assets/hellolingo1.png",
            allow_stretch=True,
            size_hint_y=0.40,
            keep_ratio=False,
        )

        # 3) Services row (15% weight)
        scroll = ScrollView(do_scroll_x=True, do_scroll_y=False, size_hint_y=0.15)
        service_grid = GridLayout(
            cols=len(self.get_services()),
            spacing=14,
            size_hint_x=None,
            row_default_height=140
        )
        service_grid.bind(minimum_width=service_grid.setter('width'))
        for ico, lbl in self.get_services():
            service_grid.add_widget(self.create_service_card(ico, lbl))
        scroll.add_widget(service_grid)

        # 4) Ads carousel (35% weight)
        ad_carousel = self.create_ad_carousel()
        if ad_carousel:
            ad_carousel.size_hint_y = 0.35

        # 5) Action row (10% weight)
        action_row = BoxLayout(orientation='horizontal', spacing=12, size_hint_y=0.10)
        action_row.add_widget(self.create_icon_button(
            "assets/user-language.png", "ابدأ الترجمة", (1,0.4,0,1), "translator"
        ))
        action_row.add_widget(self.create_icon_button(
            "assets/gamepad (1).png", "ابدأ اللعب", (0.2,0.4,0.9,1), "sign_match"
        ))

        # 6) Daily sign card (20% weight)
        daily_box = BoxLayout(orientation='horizontal', size_hint_y=0.20, spacing=0, padding=0)
        with daily_box.canvas.before:
            Color(0,0,0,0.30)
            daily_box.shadow = RoundedRectangle(
                radius=[50],
                pos=(daily_box.x+4,daily_box.y-4),
                size=daily_box.size
            )
            Color(1,1,1,1)
            daily_box.bg = RoundedRectangle(
                radius=[50],
                pos=daily_box.pos,
                size=daily_box.size
            )
        daily_box.bind(pos=self._update_daily_bg, size=self._update_daily_bg)

        # left panel
        left = BoxLayout(orientation='horizontal', size_hint=(0.7,1), padding=14, spacing=14)
        img_path = os.path.join("datapics", self.daily_sign['image'])
        icon_img = KivyImage(
            source=img_path,
            size_hint=(0.3,1),
            allow_stretch=True
        )
        left.bind(size=lambda w,*a: None)
        text_blk = BoxLayout(orientation='vertical', size_hint=(0.7,1), padding=(12,0), spacing=6)
        t1 = Label(
            text=rtl("إشارة اليوم"),
            font_name="Amiri", font_size=26, bold=True,
            color=(0.1,0.1,0.1,1),
            halign='left', valign='middle'
        )
        t1.bind(size=t1.setter('text_size'))
        t2 = Label(
            text=rtl(f"كلمة: {self.daily_sign['word']}"),
            font_name="Amiri", font_size=24, bold=True,
            color=(0.1,0.1,0.1,1),
            halign='left', valign='middle'
        )
        t2.bind(size=t2.setter('text_size'))
        text_blk.add_widget(t1)
        text_blk.add_widget(t2)
        left.add_widget(icon_img)
        left.add_widget(text_blk)

        # right panel
        right = BoxLayout(orientation='vertical', size_hint=(0.3,1))
        with right.canvas.before:
            Color(1,0.5,0.1,1)
            right.bg = RoundedRectangle(
                radius=[(0,0),(32,32),(32,32),(0,0)],
                pos=right.pos,
                size=right.size
            )
        right.bind(pos=self._update_daily_bg, size=self._update_daily_bg)
        watch = Label(
            text=rtl("👁️\nشاهد الإشارة"),
            font_name="Amiri", font_size=24, bold=True,
            color=(1,1,1,1),
            halign='center', valign='middle'
        )
        watch.bind(size=watch.setter('text_size'))
        right.bind(on_touch_down=lambda w, t: self._on_watch_touch(w, t))
        right.add_widget(watch)

        daily_box.add_widget(left)
        daily_box.add_widget(right)

        # 7) Contact bar (10% weight)
        contact_bar = BoxLayout(orientation='vertical', spacing=8, size_hint_y=0.10, padding=12)
        with contact_bar.canvas.before:
            Color(1,0.85,0.7,1)
            contact_bar.bg = RoundedRectangle(
                radius=[30],
                pos=contact_bar.pos,
                size=contact_bar.size
            )
        contact_bar.bind(pos=lambda w,*a: setattr(contact_bar.bg,'pos',contact_bar.pos))
        contact_bar.bind(size=lambda w,*a: setattr(contact_bar.bg,'size',contact_bar.size))
        msg = Label(
            text=rtl("لإعلاناتكم تواصلوا معنا على:"),
            font_name="Amiri", font_size=20, bold=True,
            halign='center', valign='middle',
            color=(0.2,0.2,0.2,1),
            size_hint=(1,0.5)
        )
        msg.bind(size=msg.setter('text_size'))
        icons = [
            ("assets/icons/email.png",    "mailto:slingoapp@gmail.com"),
            ("assets/icons/whatsapp.png", "https://wa.me/213696321064"),
            ("assets/icons/instagram.png","https://instagram.com/slingo_app")
        ]
        btn_row = BoxLayout(orientation='horizontal', spacing=14, size_hint=(1,0.5))
        for ico, link in icons:
            wrap = BoxLayout(size_hint=(1,1), padding=8)
            with wrap.canvas.before:
                Color(1,0.5,0.1,1)
                wrap.bg = RoundedRectangle(radius=[30], pos=wrap.pos, size=wrap.size)
            wrap.bind(pos=lambda w,*a: setattr(w.bg,'pos',w.pos))
            wrap.bind(size=lambda w,*a: setattr(w.bg,'size',w.size))
            btn = IconButton(
                source=ico,
                size_hint=(None,None),
                size=(48,48),
                allow_stretch=True
            )
            btn.bind(on_release=lambda _, l=link: webbrowser.open(l))
            wrap.add_widget(btn)
            btn_row.add_widget(wrap)

        contact_bar.add_widget(msg)
        contact_bar.add_widget(btn_row)

        # assemble layout
        self.layout.add_widget(top)
        self.layout.add_widget(lingo_banner)
        self.layout.add_widget(scroll)
        if ad_carousel:
            self.layout.add_widget(ad_carousel)
        self.layout.add_widget(action_row)
        self.layout.add_widget(daily_box)
        self.layout.add_widget(contact_bar)

    # ... rest of methods unchanged ...

    # ... rest of methods unchanged ...

    def load_random_daily_sign(self):
        try:
            with open("words.json", "r", encoding="utf-8") as f:
                words = json.load(f)
        except:
            words = []
        return random.choice(words) if words else {"word":"", "image":""}

    def get_services(self):
        return [
            ("hand-paper.png", "لغة الإشارة"),
            ("translate.png",  "الترجمة"),
            ("gamepad.png",    "الألعاب"),
            ("puzzle-piece.png","التدريب"),
            ("camera.png",     "الكاميرا"),
            ("file-pdf.png",   "ملفات PDF"),
            ("qr-scan.png",    "الماسح"),
            ("circle-microphone.png","التعرف الصوتي")
        ]

    def create_service_card(self, icon, label_text):
        box = BoxLayout(orientation='vertical', spacing=6,
                        size_hint=(None,None), width=90, height=100)
        with box.canvas.before:
            Color(0,0,0,0.30)
            box.shadow = RoundedRectangle(radius=[24],
                pos=(box.x+4,box.y-4), size=box.size)
            Color(1,1,1,1)
            box.bg = RoundedRectangle(radius=[24],
                pos=box.pos, size=box.size)
        box.bind(pos=self._update_box_bg, size=self._update_box_bg)

        icon_img = KivyImage(
            source=f"assets/{icon}",
            size_hint=(1,0.5),
            allow_stretch=True
        )
        lbl = Label(
            text=rtl(label_text),
            font_name="Amiri", font_size=18, bold=True,
            color=(0.1,0.1,0.1,1),
            halign='center', valign='middle',
            size_hint=(1,0.5)
        )
        lbl.bind(size=lbl.setter('text_size'))

        box.add_widget(icon_img)
        box.add_widget(lbl)
        return box

    def create_icon_button(self, icon_path, text, bg_color, target_screen):
        box = BoxLayout(orientation='horizontal', spacing=12,
                        padding=18, size_hint=(0.5,1))
        with box.canvas.before:
            Color(0,0,0,0.30)
            box.shadow = RoundedRectangle(radius=[50],
                pos=(box.x+4,box.y-4), size=box.size)
            Color(*bg_color)
            box.bg = RoundedRectangle(radius=[50],
                pos=box.pos, size=box.size)
        box.bind(pos=self._update_box_bg, size=self._update_box_bg)

        icon = KivyImage(source=icon_path, size_hint=(0.25,1), allow_stretch=True)
        lbl  = Label(
            text=rtl(text),
            font_name="Amiri", font_size=24, bold=True,
            color=(1,1,1,1),
            halign='center', valign='middle',
            size_hint=(0.75,1)
        )
        lbl.bind(size=lbl.setter('text_size'))
        box.add_widget(icon)
        box.add_widget(lbl)

        def go(inst, touch):
            if box.collide_point(*touch.pos):
                self.manager.current = target_screen
        box.bind(on_touch_down=go)
        return box

    def load_ads_data(self):
        try:
            with open("ads.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            return [ad for ad in data
                    if all(k in ad for k in ("image","title","details","link"))]
        except:
            return []

    def create_ad_carousel(self):
        ads = self.load_ads_data()
        if not ads:
            return None
        carousel = Carousel(direction='right', loop=True)
        for ad in ads:
            img = KivyImage(source=ad["image"], allow_stretch=True)
            img.ad_data = ad
            img.bind(on_touch_down=self.show_ad_popup)
            carousel.add_widget(img)
        Clock.schedule_interval(lambda dt: carousel.load_next(), 5)
        return carousel

    def show_ad_popup(self, widget, touch):
        if not widget.collide_point(*touch.pos):
            return
        ad = widget.ad_data
        popup = ModalView(size_hint=(0.9,0.6), auto_dismiss=False)
        box = BoxLayout(orientation='vertical', padding=24, spacing=16)
        with box.canvas.before:
            Color(0,0,0,0.8)
            box.bg = RoundedRectangle(radius=[20], pos=box.pos, size=box.size)
        box.bind(pos=lambda w,*a: setattr(box.bg,'pos',w.pos))
        box.bind(size=lambda w,*a: setattr(box.bg,'size',w.size))

        ad_img = KivyImage(source=ad["image"], size_hint=(1,0.4), allow_stretch=True)
        title = Label(
            text=rtl(ad["title"]),
            font_name="Amiri", font_size=28, bold=True,
            color=(1,0.5,0.1,1),
            halign='center', valign='middle',
            size_hint=(1,0.15)
        )
        title.bind(size=title.setter('text_size'))
        details = Label(
            text=rtl(ad["details"]),
            font_name="Amiri", font_size=24, bold=True,
            color=(1,1,1,1),
            halign='center', valign='middle',
            size_hint=(1,0.25)
        )
        details.bind(size=details.setter('text_size'))

        btn_row = BoxLayout(orientation='horizontal', spacing=12, size_hint=(1,0.20))
        contact_btn = Button(
            text=rtl("📧 تواصل الآن"),
            font_name="Amiri", font_size=22, bold=True,
            background_normal="", background_color=(1,0.5,0.1,1)
        )
        with contact_btn.canvas.before:
            Color(1,0.5,0.1,1)
            contact_btn.bg = RoundedRectangle(radius=[40], pos=contact_btn.pos, size=contact_btn.size)
        contact_btn.bind(pos=self._update_popup_btn_bg, size=self._update_popup_btn_bg)
        contact_btn.bind(on_release=lambda _: webbrowser.open(ad["link"]))

        close_btn = Button(
            text=rtl("إغلاق"),
            font_name="Amiri", font_size=22, bold=True,
            background_normal="", background_color=(0.3,0.3,0.3,1)
        )
        with close_btn.canvas.before:
            Color(0.3,0.3,0.3,1)
            close_btn.bg = RoundedRectangle(radius=[40], pos=close_btn.pos, size=close_btn.size)
        close_btn.bind(pos=self._update_popup_btn_bg, size=self._update_popup_btn_bg)
        close_btn.bind(on_release=lambda _: popup.dismiss())

        btn_row.add_widget(contact_btn)
        btn_row.add_widget(close_btn)

        box.add_widget(ad_img)
        box.add_widget(title)
        box.add_widget(details)
        box.add_widget(btn_row)
        popup.add_widget(box)
        popup.open()

    def play_daily_sign(self):
        word = self.daily_sign.get('word','')
        if not word: return
        video_dir = "datavideos"
        tmp = tempfile.gettempdir()
        list_txt = os.path.join(tmp, f"{word}_list.txt")
        out_mp4  = os.path.join(tmp, f"{word}_daily.mp4")
        with open(list_txt, "w", encoding="utf-8") as f:
            for c in word:
                path = os.path.join(video_dir, f"{c}.mp4")
                if os.path.exists(path):
                    p = os.path.abspath(path).replace("\\","/")
                    f.write(f"file '{p}'\n")
        if not os.path.exists(out_mp4):
            subprocess.run([
                "ffmpeg","-y","-f","concat","-safe","0",
                "-i", list_txt, "-c","copy", out_mp4
            ], check=True)
        if not hasattr(self, 'daily_video'):
            from kivy.uix.video import Video
            self.daily_video = Video(size_hint=(1,0.3), state='stop',
                                     options={'eos':'loop'})
            self.layout.add_widget(self.daily_video)
        else:
            if self.daily_video.parent is None:
                self.layout.add_widget(self.daily_video)
        self.daily_video.source = out_mp4
        self.daily_video.state = 'play'

    def _update_box_bg(self, widget, _):
        if hasattr(widget, 'shadow'):
            widget.shadow.pos = (widget.x+4, widget.y-4)
            widget.shadow.size = widget.size
        if hasattr(widget, 'bg'):
            widget.bg.pos = widget.pos
            widget.bg.size = widget.size

    def _update_daily_bg(self, widget, _):
        if hasattr(widget, 'shadow'):
            widget.shadow.pos = (widget.x+4, widget.y-4)
            widget.shadow.size = widget.size
        if hasattr(widget, 'bg'):
            widget.bg.pos = widget.pos
            widget.bg.size = widget.size

    def _update_popup_btn_bg(self, widget, _):
        if hasattr(widget, 'bg'):
            widget.bg.pos = widget.pos
            widget.bg.size = widget.size

    def _on_watch_touch(self, widget, touch):
        if widget.collide_point(*touch.pos):
            self.play_daily_sign()

# screens/admin_dashboard.py

import os
import json
import webbrowser

from kivy.core.text import LabelBase
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import ButtonBehavior
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.screenmanager import Screen

import arabic_reshaper
from bidi.algorithm import get_display

# ─── Register Arabic font ────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "..", "fonts", "Amiri-Regular.ttf")
if os.path.isfile(FONT_PATH):
    LabelBase.register(name="Amiri", fn_regular=FONT_PATH)

def rtl(text: str) -> str:
    """Reshape & reorder Arabic text for correct display."""
    return get_display(arabic_reshaper.reshape(text))


class RtlTextInput(TextInput):
    """Live-reshaping, right-to-left TextInput with recursion guard."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.original_text = ""
        self._updating = False
        self.font_name = "Amiri"
        self.halign = "right"
        self.cursor_blink = True

    def insert_text(self, substring, from_undo=False):
        # Append raw input, then rebuild the display text
        self.original_text += substring
        self._update_display()

    def do_backspace(self, from_undo=False, mode='bkspc'):
        # Remove last char, then rebuild
        if self.original_text:
            self.original_text = self.original_text[:-1]
            self._update_display()

    def _update_display(self):
        if self._updating:
            return
        self._updating = True
        # Reshape & bidi each line
        lines = self.original_text.splitlines()
        shaped = "\n".join(rtl(line) for line in lines)
        # Remember cursor position
        idx = self.cursor_index()
        self.text = shaped
        # Restore logical cursor
        self.cursor = self.get_cursor_from_index(idx)
        self._updating = False


class LabelButton(ButtonBehavior, Label):
    """A Label that can receive on_release, on_touch_down, etc."""
    pass


class IconTextButton(ButtonBehavior, BoxLayout):
    """
    A clickable horizontal layout containing an icon + label.
    Usage:
        IconTextButton(icon="path/to/icon.png", text="Some Label", on_release=callback)
    """
    def __init__(self, icon: str, text: str, **kwargs):
        super().__init__(orientation="horizontal", spacing=8, padding=(16, 12), **kwargs)
        self.size_hint = (1, None)
        self.height = 72

        with self.canvas.before:
            Color(1, 0.6, 0.2, 1)  # bright orange
            self._bg = RoundedRectangle(radius=[24], pos=self.pos, size=self.size)
        self.bind(pos=lambda w, *_: setattr(self._bg, "pos", w.pos))
        self.bind(size=lambda w, *_: setattr(self._bg, "size", w.size))

        self.icon = KivyImage(
            source=icon,
            size_hint=(None, None),
            size=(32, 32),
            allow_stretch=True
        )
        self.icon.pos_hint = {"center_y": 0.5}
        self.add_widget(self.icon)

        self.label = Label(
            text=rtl(text),
            font_name="Amiri",
            font_size=22,
            bold=True,
            color=(1, 1, 1, 1),
            halign="left",
            valign="middle"
        )
        self.label.bind(size=self.label.setter("text_size"))
        self.label.size_hint = (1, 1)
        self.add_widget(self.label)


class DashboardScreen(Screen):
    """
    Admin Dashboard: manage Users, Words, and Ads JSON files.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Paths to JSON files
        self.users_file = os.path.join(BASE_DIR, "..", "users.json")
        self.words_file = os.path.join(BASE_DIR, "..", "words.json")
        self.ads_file   = os.path.join(BASE_DIR, "..", "ads.json")

        # ─── Root Layout: (sidebar | content) ───────────────────────────────
        self.root_layout = BoxLayout(orientation="horizontal", spacing=0)
        self.add_widget(self.root_layout)

        # ─── Sidebar ───────────────────────────────────────────────────────
        self.sidebar = BoxLayout(
            orientation="vertical",
            size_hint=(0.25, 1),
            spacing=16,
            padding=(8, 16)
        )
        with self.sidebar.canvas.before:
            Color(1, 0.5, 0.1, 1)  # Bright orange
            self._sidebar_bg = RoundedRectangle(radius=[0], pos=self.sidebar.pos, size=self.sidebar.size)
        self.sidebar.bind(pos=lambda w, *_: setattr(self._sidebar_bg, "pos", w.pos))
        self.sidebar.bind(size=lambda w, *_: setattr(self._sidebar_bg, "size", w.size))

        # 1) Admin avatar
        boss_icon = KivyImage(
            source="assets/icons/boss.png",
            size_hint=(None, None),
            size=(64, 64),
            allow_stretch=True
        )
        boss_icon.pos_hint = {"center_x": 0.5}
        self.sidebar.add_widget(boss_icon)

        # 2) Navigation buttons
        self.btn_users = IconTextButton(icon="assets/icons/users-alt.png", text="المستخدمون")
        self.btn_users.bind(on_release=lambda inst: self.switch_section("users"))
        self.sidebar.add_widget(self.btn_users)

        self.btn_words = IconTextButton(icon="assets/icons/game.png", text="الكلمات")
        self.btn_words.bind(on_release=lambda inst: self.switch_section("words"))
        self.sidebar.add_widget(self.btn_words)

        self.btn_ads = IconTextButton(icon="assets/icons/ad-paid.png", text="الإعلانات")
        self.btn_ads.bind(on_release=lambda inst: self.switch_section("ads"))
        self.sidebar.add_widget(self.btn_ads)

        # Spacer
        self.sidebar.add_widget(Label(size_hint=(1, 1)))

        # Sign out button
        self.btn_signout = LabelButton(
            text=rtl("تسجيل الخروج"),
            font_name="Amiri",
            font_size=22,
            bold=True,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        self.btn_signout.size_hint = (1, None)
        self.btn_signout.height = 64
        with self.btn_signout.canvas.before:
            Color(0.8, 0.1, 0.1, 1)  # Dark red background
            self._signout_bg = RoundedRectangle(radius=[24], pos=self.btn_signout.pos, size=self.btn_signout.size)
        self.btn_signout.bind(pos=lambda w, *_: setattr(self._signout_bg, "pos", w.pos))
        self.btn_signout.bind(size=lambda w, *_: setattr(self._signout_bg, "size", w.size))
        self.btn_signout.bind(on_release=self.do_signout)
        self.sidebar.add_widget(self.btn_signout)

        self.root_layout.add_widget(self.sidebar)

        # ─── Content area ───────────────────────────────────────────────────
        self.content_area = BoxLayout(orientation="vertical", padding=(24, 16), spacing=24)
        self.root_layout.add_widget(self.content_area)

        # Header label
        self.header_label = Label(
            text=rtl("لوحة التحكم – مرحبًا، مشرف!"),
            font_name="Amiri",
            font_size=34,
            bold=True,
            color=(0.03, 0.03, 0.03, 1),
            size_hint=(1, None),
            height=72,
            halign="left",
            valign="middle"
        )
        self.header_label.bind(size=self.header_label.setter("text_size"))
        self.content_area.add_widget(self.header_label)

        # Search + “+ Add” row
        search_add_box = BoxLayout(size_hint=(1, None), height=64, spacing=12)
        with search_add_box.canvas.before:
            Color(0.95, 0.95, 0.95, 1)
            search_add_box.bg = RoundedRectangle(radius=[32], pos=search_add_box.pos, size=search_add_box.size)
        search_add_box.bind(pos=lambda w, *_: setattr(search_add_box.bg, "pos", w.pos))
        search_add_box.bind(size=lambda w, *_: setattr(search_add_box.bg, "size", w.size))

        # ─ Search input (hint in Arabic)
        self.search_input = RtlTextInput(
            hint_text=rtl("ابحث..."),
            font_size=20,
            size_hint=(0.75, 1),
            multiline=False,
            foreground_color=(0.1, 0.1, 0.1, 1),
            background_color=(1, 1, 1, 0),
            padding=(16, 12),
        )
        search_icon = KivyImage(
            source="assets/icons/search.png",
            size_hint=(None, None),
            size=(36, 36),
            allow_stretch=True
        )
        search_box = BoxLayout(orientation="horizontal", size_hint=(0.75, 1), padding=(12, 0), spacing=8)
        search_box.add_widget(self.search_input)
        search_box.add_widget(search_icon)

        # ─ “+ إضافة جديد” button
        self.add_btn = LabelButton(
            text=rtl("+ إضافة جديد"),
            font_name="Amiri",
            font_size=20,
            bold=True,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        self.add_btn.size_hint = (0.25, 1)
        with self.add_btn.canvas.before:
            Color(1, 0.5, 0.1, 1)
            self._add_btn_bg = RoundedRectangle(radius=[32], pos=self.add_btn.pos, size=self.add_btn.size)
        self.add_btn.bind(pos=lambda w, *_: setattr(self._add_btn_bg, "pos", w.pos))
        self.add_btn.bind(size=lambda w, *_: setattr(self._add_btn_bg, "size", w.size))
        self.add_btn.bind(on_release=lambda inst: self.open_add_popup())

        search_add_box.add_widget(search_box)
        search_add_box.add_widget(self.add_btn)
        self.content_area.add_widget(search_add_box)

        # Separator line
        with self.content_area.canvas:
            Color(0.85, 0.85, 0.85, 1)
            self._sep_line = RoundedRectangle(
                radius=[0],
                pos=(self.content_area.x, self.content_area.y + self.content_area.height - 160),
                size=(self.content_area.width, 2)
            )
        self.content_area.bind(size=lambda w, *_: setattr(self._sep_line, "size", (w.width, 2)))
        self.content_area.bind(pos=lambda w, *_: setattr(self._sep_line, "pos", (w.x, w.y + w.height - 160)))

        # Scrollable Grid for listing rows
        self.scrollview = ScrollView(size_hint=(1, 1))
        self.list_grid = GridLayout(
            cols=1,
            spacing=12,
            padding=(0, 0, 0, 12),
            size_hint_y=None
        )
        self.list_grid.bind(minimum_height=self.list_grid.setter("height"))
        self.scrollview.add_widget(self.list_grid)
        self.content_area.add_widget(self.scrollview)

        # Track active section & bind search
        self.active_section = "users"
        self.search_input.bind(text=lambda inst, val: self.refresh_list())

        # Initially load “users” section
        self.switch_section("users")


    # ─── SIGN OUT ───────────────────────────────────────────────────────────────
    def do_signout(self, instance):
        from kivy.app import App
        App.get_running_app().current_user = None
        self.manager.current = "login"


    # ─── SECTION SWITCHING ─────────────────────────────────────────────────────
    def switch_section(self, section):
        self.active_section = section

        # Reset sidebar buttons
        for btn in (self.btn_users, self.btn_words, self.btn_ads):
            btn.canvas.before.clear()
            with btn.canvas.before:
                Color(1, 0.6, 0.2, 1)
                btn._bg = RoundedRectangle(radius=[24], pos=btn.pos, size=btn.size)
            btn.bind(pos=lambda w, *_: setattr(btn._bg, "pos", w.pos))
            btn.bind(size=lambda w, *_: setattr(btn._bg, "size", w.size))

        # Highlight active
        if section == "users":
            with self.btn_users.canvas.before:
                Color(1, 0.35, 0.05, 1)
                self.btn_users._bg = RoundedRectangle(radius=[24], pos=self.btn_users.pos, size=self.btn_users.size)
            self.header_label.text = rtl("لوحة التحكم – قائمة المستخدمين")
            self.add_btn.text = rtl("+ إضافة مستخدم جديد")

        elif section == "words":
            with self.btn_words.canvas.before:
                Color(1, 0.35, 0.05, 1)
                self.btn_words._bg = RoundedRectangle(radius=[24], pos=self.btn_words.pos, size=self.btn_words.size)
            self.header_label.text = rtl("لوحة التحكم – إدارة الكلمات")
            self.add_btn.text = rtl("+ إضافة كلمة جديدة")

        else:  # ads
            with self.btn_ads.canvas.before:
                Color(1, 0.35, 0.05, 1)
                self.btn_ads._bg = RoundedRectangle(radius=[24], pos=self.btn_ads.pos, size=self.btn_ads.size)
            self.header_label.text = rtl("لوحة التحكم – إدارة الإعلانات")
            self.add_btn.text = rtl("+ إضافة إعلان جديد")

        # Reset search & reload
        self.search_input.original_text = ""
        self.search_input.text = ""
        self.refresh_list()


    def refresh_list(self):
        self.list_grid.clear_widgets()
        query = self.search_input.original_text.strip().lower()

        if self.active_section == "users":
            self._load_users(query)
        elif self.active_section == "words":
            self._load_words(query)
        else:
            self._load_ads(query)


    def open_add_popup(self):
        if self.active_section == "users":
            self._open_user_popup(editing=False, username="")
        elif self.active_section == "words":
            self._open_word_popup(editing=False, word_name="")
        else:
            self._open_ad_popup(editing=False, ad_index=None)


    # ─── UTILITY: CREATE HEADER ROW ────────────────────────────────────────────
    def _make_list_header(self, columns):
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=64, spacing=12, padding=(12, 0))
        num_cols = len(columns)
        for col in columns:
            lbl = Label(
                text=col,
                font_name="Amiri",
                font_size=24,
                bold=True,
                color=(0.05, 0.05, 0.05, 1),
                size_hint=(1.0 / num_cols, 1),
                halign="center",
                valign="middle"
            )
            lbl.bind(size=lbl.setter("text_size"))
            header.add_widget(lbl)
        return header


    # ─── USERS SECTION ────────────────────────────────────────────────────────
    def _load_users(self, query=""):
        try:
            with open(self.users_file, "r", encoding="utf-8") as f:
                users_data = json.load(f)
        except Exception:
            users_data = {}

        header = self._make_list_header(["", rtl("اسم المستخدم"), rtl("كلمة المرور"), "", ""])
        self.list_grid.add_widget(header)

        for uname, pdata in users_data.items():
            if query and query not in uname.lower():
                continue

            pwd = pdata.get("password", "")
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=64, spacing=12, padding=(12, 0))

            # User icon
            icon_user = KivyImage(
                source="assets/icons/users-alt.png",
                size_hint=(None, None),
                size=(32, 32),
                allow_stretch=True
            )
            icon_user.pos_hint = {"center_y": 0.5}
            row.add_widget(icon_user)

            # Username
            lbl_un = Label(
                text=uname,
                font_name="Amiri",
                font_size=22,
                bold=True,
                color=(0.1, 0.1, 0.1, 1),
                size_hint=(0.30, 1),
                halign="center",
                valign="middle"
            )
            lbl_un.bind(size=lbl_un.setter("text_size"))
            row.add_widget(lbl_un)

            # Password
            lbl_pw = Label(
                text=pwd,
                font_name="Amiri",
                font_size=22,
                bold=True,
                color=(0.1, 0.1, 0.1, 1),
                size_hint=(0.30, 1),
                halign="center",
                valign="middle"
            )
            lbl_pw.bind(size=lbl_pw.setter("text_size"))
            row.add_widget(lbl_pw)

            # Edit icon
            btn_edit = KivyImage(
                source="assets/icons/pencil.png",
                size_hint=(None, None),
                size=(32, 32),
                allow_stretch=True
            )
            btn_edit.pos_hint = {"center_y": 0.5}
            btn_edit.bind(on_touch_down=lambda inst, touch, u=uname: self._on_user_edit(inst, touch, u))
            row.add_widget(btn_edit)

            # Delete icon
            btn_del = KivyImage(
                source="assets/icons/trash.png",
                size_hint=(None, None),
                size=(32, 32),
                allow_stretch=True
            )
            btn_del.pos_hint = {"center_y": 0.5}
            btn_del.bind(on_touch_down=lambda inst, touch, u=uname: self._on_user_delete(inst, touch, u))
            row.add_widget(btn_del)

            self.list_grid.add_widget(row)


    def _on_user_edit(self, widget, touch, username):
        if widget.collide_point(*touch.pos):
            self._open_user_popup(editing=True, username=username)


    def _on_user_delete(self, widget, touch, username):
        if not widget.collide_point(*touch.pos):
            return

        content = BoxLayout(orientation="vertical", padding=20, spacing=20)
        lbl = Label(
            text=rtl(f"هل أنت متأكد أنك تريد حذف المستخدم '{username}'؟"),
            font_name="Amiri",
            font_size=20,
            color=(0.1, 0.1, 0.1, 1),
            halign="center",
            valign="middle"
        )
        lbl.bind(size=lbl.setter("text_size"))

        btns = BoxLayout(spacing=20, size_hint_y=None, height=56)
        yes = LabelButton(
            text=rtl("نعم"),
            font_name="Amiri",
            font_size=20,
            bold=True,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        with yes.canvas.before:
            Color(1, 0.2, 0.2, 1)
            yes.bg = RoundedRectangle(radius=[24], pos=yes.pos, size=yes.size)
        yes.bind(pos=lambda w, *_: setattr(yes.bg, "pos", w.pos))
        yes.bind(size=lambda w, *_: setattr(yes.bg, "size", w.size))

        no = LabelButton(
            text=rtl("إلغاء"),
            font_name="Amiri",
            font_size=20,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        with no.canvas.before:
            Color(0.6, 0.6, 0.6, 1)
            no.bg = RoundedRectangle(radius=[24], pos=no.pos, size=no.size)
        no.bind(pos=lambda w, *_: setattr(no.bg, "pos", w.pos))
        no.bind(size=lambda w, *_: setattr(no.bg, "size", w.size))

        btns.add_widget(yes)
        btns.add_widget(no)
        content.add_widget(lbl)
        content.add_widget(btns)

        popup = Popup(title="", content=content, size_hint=(0.7, 0.4), auto_dismiss=False)

        def confirm_delete(inst):
            try:
                with open(self.users_file, "r+", encoding="utf-8") as f:
                    data = json.load(f)
                    data.pop(username, None)
                    f.seek(0)
                    f.truncate()
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            popup.dismiss()
            self.refresh_list()

        yes.bind(on_release=confirm_delete)
        no.bind(on_release=lambda inst: popup.dismiss())
        popup.open()


    def _open_user_popup(self, editing=False, username=""):
        title_txt = rtl("تعديل المستخدم") if editing else rtl("إضافة مستخدم جديد")
        popup = ModalView(size_hint=(0.9, 0.6), auto_dismiss=False)

        box = BoxLayout(orientation="vertical", spacing=24, padding=32)
        with box.canvas.before:
            Color(1, 1, 1, 1)
            box.bg = RoundedRectangle(radius=[24], pos=box.pos, size=box.size)
        box.bind(pos=lambda w, *_: setattr(box.bg, "pos", w.pos))
        box.bind(size=lambda w, *_: setattr(box.bg, "size", w.size))

        lbl_title = Label(
            text=title_txt,
            font_name="Amiri",
            font_size=28,
            bold=True,
            color=(0.03, 0.03, 0.03, 1),
            halign="center",
            valign="middle",
            size_hint=(1, None),
            height=56
        )
        lbl_title.bind(size=lbl_title.setter("text_size"))
        box.add_widget(lbl_title)

        inp_user = RtlTextInput(
            hint_text=rtl("اسم المستخدم"),
            text=username if editing else "",
            font_size=22,
            multiline=False,
            foreground_color=(0.1, 0.1, 0.1, 1),
            background_color=(0.95, 0.95, 0.95, 1),
            size_hint=(1, None),
            height=56
        )
        inp_pass = RtlTextInput(
            hint_text=rtl("كلمة المرور"),
            text="",
            font_size=22,
            multiline=False,
            password=True,
            foreground_color=(0.1, 0.1, 0.1, 1),
            background_color=(0.95, 0.95, 0.95, 1),
            size_hint=(1, None),
            height=56
        )

        if editing:
            try:
                with open(self.users_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    inp_pass.original_text = data.get(username, {}).get("password", "")
                    inp_pass.text = rtl(inp_pass.original_text)
            except Exception:
                inp_pass.text = ""

        box.add_widget(inp_user)
        box.add_widget(inp_pass)

        btn_save = LabelButton(
            text=rtl("حفظ"),
            font_name="Amiri",
            font_size=22,
            bold=True,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        btn_save.size_hint = (1, None)
        btn_save.height = 56
        with btn_save.canvas.before:
            Color(0.2, 0.6, 1, 1)
            btn_save.bg = RoundedRectangle(radius=[24], pos=btn_save.pos, size=btn_save.size)
        btn_save.bind(pos=lambda w, *_: setattr(btn_save.bg, "pos", w.pos))
        btn_save.bind(size=lambda w, *_: setattr(btn_save.bg, "size", w.size))

        btn_cancel = LabelButton(
            text=rtl("إلغاء"),
            font_name="Amiri",
            font_size=22,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        btn_cancel.size_hint = (1, None)
        btn_cancel.height = 56
        with btn_cancel.canvas.before:
            Color(0.6, 0.6, 0.6, 1)
            btn_cancel.bg = RoundedRectangle(radius=[24], pos=btn_cancel.pos, size=btn_cancel.size)
        btn_cancel.bind(pos=lambda w, *_: setattr(btn_cancel.bg, "pos", w.pos))
        btn_cancel.bind(size=lambda w, *_: setattr(btn_cancel.bg, "size", w.size))

        btn_box = BoxLayout(orientation="horizontal", spacing=20, size_hint_y=None, height=56)
        btn_box.add_widget(btn_save)
        btn_box.add_widget(btn_cancel)
        box.add_widget(btn_box)

        popup.add_widget(box)

        def save_user(inst):
            new_uname = inp_user.original_text.strip()
            new_pwd = inp_pass.original_text.strip()
            if not new_uname or not new_pwd:
                return
            try:
                with open(self.users_file, "r+", encoding="utf-8") as f:
                    data = json.load(f)
                    if editing and username != new_uname:
                        data.pop(username, None)
                    data[new_uname] = {"password": new_pwd}
                    f.seek(0)
                    f.truncate()
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            popup.dismiss()
            self.refresh_list()

        btn_save.bind(on_release=save_user)
        btn_cancel.bind(on_release=lambda inst: popup.dismiss())
        popup.open()


    # ─── WORDS SECTION ────────────────────────────────────────────────────────
    def _load_words(self, query=""):
        try:
            with open(self.words_file, "r", encoding="utf-8") as f:
                words_data = json.load(f)
        except Exception:
            words_data = []

        header = self._make_list_header(["", rtl("الكلمة"), rtl("الصورة"), "", ""])
        self.list_grid.add_widget(header)

        for item in words_data:
            wtext = item.get("word", "")
            wimg = item.get("image", "")
            if query and query not in wtext.lower():
                continue

            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=64,
                spacing=12,
                padding=(12, 0)
            )

            icon_word = KivyImage(
                source="assets/icons/game.png",
                size_hint=(None, None),
                size=(32, 32),
                allow_stretch=True
            )
            icon_word.pos_hint = {"center_y": 0.5}
            row.add_widget(icon_word)

            lbl_word = Label(
                text=rtl(wtext),
                font_name="Amiri",
                font_size=22,
                bold=True,
                color=(0.1, 0.1, 0.1, 1),
                size_hint=(0.35, 1),
                halign="center",
                valign="middle"
            )
            lbl_word.bind(size=lbl_word.setter("text_size"))
            row.add_widget(lbl_word)

            lbl_img = Label(
                text=rtl(os.path.basename(wimg)),
                font_name="Amiri",
                font_size=20,
                color=(0.2, 0.2, 0.2, 1),
                size_hint=(0.40, 1),
                halign="center",
                valign="middle"
            )
            lbl_img.bind(size=lbl_img.setter("text_size"))
            row.add_widget(lbl_img)

            btn_edit = KivyImage(
                source="assets/icons/pencil.png",
                size_hint=(None, None),
                size=(32, 32),
                allow_stretch=True
            )
            btn_edit.pos_hint = {"center_y": 0.5}
            btn_edit.bind(on_touch_down=lambda inst, touch, wn=wtext: self._on_word_edit(inst, touch, wn))
            row.add_widget(btn_edit)

            btn_del = KivyImage(
                source="assets/icons/trash.png",
                size_hint=(None, None),
                size=(32, 32),
                allow_stretch=True
            )
            btn_del.pos_hint = {"center_y": 0.5}
            btn_del.bind(on_touch_down=lambda inst, touch, wn=wtext: self._on_word_delete(inst, touch, wn))
            row.add_widget(btn_del)

            self.list_grid.add_widget(row)


    def _on_word_edit(self, widget, touch, word_name):
        if widget.collide_point(*touch.pos):
            self._open_word_popup(editing=True, word_name=word_name)


    def _on_word_delete(self, widget, touch, word_name):
        if not widget.collide_point(*touch.pos):
            return

        content = BoxLayout(orientation="vertical", padding=20, spacing=20)
        lbl = Label(
            text=rtl(f"هل أنت متأكد أنك تريد حذف الكلمة '{word_name}'؟"),
            font_name="Amiri",
            font_size=20,
            color=(0.1, 0.1, 0.1, 1),
            halign="center",
            valign="middle"
        )
        lbl.bind(size=lbl.setter("text_size"))

        btns = BoxLayout(spacing=20, size_hint_y=None, height=56)
        yes = LabelButton(
            text=rtl("نعم"),
            font_name="Amiri",
            font_size=20,
            bold=True,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        with yes.canvas.before:
            Color(1, 0.2, 0.2, 1)
            yes.bg = RoundedRectangle(radius=[24], pos=yes.pos, size=yes.size)
        yes.bind(pos=lambda w, *_: setattr(yes.bg, "pos", w.pos))
        yes.bind(size=lambda w, *_: setattr(yes.bg, "size", w.size))

        no = LabelButton(
            text=rtl("إلغاء"),
            font_name="Amiri",
            font_size=20,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        with no.canvas.before:
            Color(0.6, 0.6, 0.6, 1)
            no.bg = RoundedRectangle(radius=[24], pos=no.pos, size=no.size)
        no.bind(pos=lambda w, *_: setattr(no.bg, "pos", w.pos))
        no.bind(size=lambda w, *_: setattr(no.bg, "size", w.size))

        btns.add_widget(yes)
        btns.add_widget(no)
        content.add_widget(lbl)
        content.add_widget(btns)

        popup = Popup(title="", content=content, size_hint=(0.7, 0.4), auto_dismiss=False)

        def confirm_delete(inst):
            try:
                with open(self.words_file, "r+", encoding="utf-8") as f:
                    arr = json.load(f)
                    arr = [it for it in arr if it.get("word") != word_name]
                    f.seek(0)
                    f.truncate()
                    json.dump(arr, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            popup.dismiss()
            self.refresh_list()

        yes.bind(on_release=confirm_delete)
        no.bind(on_release=lambda inst: popup.dismiss())
        popup.open()


    def _open_word_popup(self, editing=False, word_name=""):
        title_txt = rtl("تعديل كلمة") if editing else rtl("إضافة كلمة جديدة")
        popup = ModalView(size_hint=(0.9, 0.75), auto_dismiss=False)

        box = BoxLayout(orientation="vertical", padding=24, spacing=24)
        with box.canvas.before:
            Color(1, 1, 1, 1)
            box.bg = RoundedRectangle(radius=[24], pos=box.pos, size=box.size)
        box.bind(pos=lambda w, *_: setattr(box.bg, "pos", w.pos))
        box.bind(size=lambda w, *_: setattr(box.bg, "size", w.size))

        lbl_title = Label(
            text=title_txt,
            font_name="Amiri",
            font_size=26,
            bold=True,
            color=(0.03, 0.03, 0.03, 1),
            halign="center",
            valign="middle",
            size_hint=(1, None),
            height=56
        )
        lbl_title.bind(size=lbl_title.setter("text_size"))
        box.add_widget(lbl_title)

        inp_word = RtlTextInput(
            hint_text=rtl("الكلمة (نص عربي)"),
            text=word_name if editing else "",
            font_size=22,
            multiline=False,
            foreground_color=(0.1, 0.1, 0.1, 1),
            background_color=(0.95, 0.95, 0.95, 1),
            size_hint=(1, None),
            height=56
        )
        inp_img = RtlTextInput(
            hint_text=rtl("مسار الصورة (اضغط للاختيار)"),
            text="",
            font_size=20,
            multiline=False,
            readonly=True,
            foreground_color=(0.1, 0.1, 0.1, 1),
            background_color=(0.95, 0.95, 0.95, 1),
            size_hint=(1, None),
            height=56
        )

        if editing:
            try:
                with open(self.words_file, "r", encoding="utf-8") as f:
                    arr = json.load(f)
                    for it in arr:
                        if it.get("word") == word_name:
                            inp_word.original_text = it.get("word", "")
                            inp_word.text = rtl(inp_word.original_text)
                            inp_img.original_text = it.get("image", "")
                            inp_img.text = rtl(inp_img.original_text)
                            break
            except Exception:
                pass

        btn_select = LabelButton(
            text=rtl("🖼️ اختر صورة"),
            font_name="Amiri",
            font_size=20,
            bold=True,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        btn_select.size_hint = (1, None)
        btn_select.height = 56
        with btn_select.canvas.before:
            Color(0.2, 0.6, 1, 1)
            btn_select.bg = RoundedRectangle(radius=[24], pos=btn_select.pos, size=btn_select.size)
        btn_select.bind(pos=lambda w, *_: setattr(btn_select.bg, "pos", w.pos))
        btn_select.bind(size=lambda w, *_: setattr(btn_select.bg, "size", w.size))

        def open_filechooser(inst):
            chooser = FileChooserIconView(filters=["*.png", "*.jpg", "*.jpeg"], size_hint=(1, 1))
            popup_fc = Popup(title=rtl("اختر صورة"), content=chooser, size_hint=(0.9, 0.9))

            def on_file_select(fc, selection, touch=None):
                if selection:
                    inp_img.original_text = selection[0]
                    inp_img.text = rtl(inp_img.original_text)
                    popup_fc.dismiss()

            chooser.bind(on_submit=lambda fc, sel, touch: on_file_select(fc, sel, touch))
            popup_fc.open()

        btn_select.bind(on_release=open_filechooser)

        box.add_widget(inp_word)
        box.add_widget(inp_img)
        box.add_widget(btn_select)

        btn_save = LabelButton(
            text=rtl("حفظ"),
            font_name="Amiri",
            font_size=20,
            bold=True,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        btn_save.size_hint = (1, None)
        btn_save.height = 56
        with btn_save.canvas.before:
            Color(0.2, 0.6, 1, 1)
            btn_save.bg = RoundedRectangle(radius=[24], pos=btn_save.pos, size=btn_save.size)
        btn_save.bind(pos=lambda w, *_: setattr(btn_save.bg, "pos", w.pos))
        btn_save.bind(size=lambda w, *_: setattr(btn_save.bg, "size", w.size))

        btn_cancel = LabelButton(
            text=rtl("إلغاء"),
            font_name="Amiri",
            font_size=20,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        btn_cancel.size_hint = (1, None)
        btn_cancel.height = 56
        with btn_cancel.canvas.before:
            Color(0.6, 0.6, 0.6, 1)
            btn_cancel.bg = RoundedRectangle(radius=[24], pos=btn_cancel.pos, size=btn_cancel.size)
        btn_cancel.bind(pos=lambda w, *_: setattr(btn_cancel.bg, "pos", w.pos))
        btn_cancel.bind(size=lambda w, *_: setattr(btn_cancel.bg, "size", w.size))

        btn_box = BoxLayout(orientation="horizontal", spacing=20, size_hint_y=None, height=56)
        btn_box.add_widget(btn_save)
        btn_box.add_widget(btn_cancel)
        box.add_widget(btn_box)

        popup.add_widget(box)

        def save_word(inst):
            new_wtext = inp_word.original_text.strip()
            new_wimg = inp_img.original_text.strip()
            if not new_wtext or not new_wimg:
                return
            try:
                with open(self.words_file, "r+", encoding="utf-8") as f:
                    arr = json.load(f)
                    if editing:
                        for it in arr:
                            if it.get("word") == word_name:
                                it["word"] = new_wtext
                                it["image"] = new_wimg
                                break
                    else:
                        arr.append({"word": new_wtext, "image": new_wimg})
                    f.seek(0)
                    f.truncate()
                    json.dump(arr, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            popup.dismiss()
            self.refresh_list()

        btn_save.bind(on_release=save_word)
        btn_cancel.bind(on_release=lambda inst: popup.dismiss())
        popup.open()


    # ─── ADS SECTION ─────────────────────────────────────────────────────────
    def _load_ads(self, query=""):
        try:
            with open(self.ads_file, "r", encoding="utf-8") as f:
                ads_data = json.load(f)
        except Exception:
            ads_data = []

        header = self._make_list_header(
            ["", rtl("عنوان الإعلان"), rtl("التفاصيل"), rtl("الصورة"), "", ""]
        )
        self.list_grid.add_widget(header)

        for idx, item in enumerate(ads_data):
            full_title   = item.get("title", "")
            full_details = item.get("details", "").replace("\n", " ")
            img_path     = item.get("image", "")

            if query and query not in full_title.lower():
                continue

            max_words = 2
            title_words = full_title.split()
            title_short = " ".join(title_words[:max_words]).rstrip() + ("..." if len(title_words) > max_words else "")
            details_words = full_details.split()
            details_short = " ".join(details_words[:max_words]).rstrip() + ("..." if len(details_words) > max_words else "")

            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=72,
                spacing=12,
                padding=(12, 0)
            )

            icon_ad = KivyImage(
                source="assets/icons/ad-paid.png",
                size_hint=(None, None),
                size=(32, 32),
                allow_stretch=True
            )
            icon_ad.pos_hint = {"center_y": 0.5}
            row.add_widget(icon_ad)

            lbl_title = Label(
                text=rtl(title_short),
                font_name="Amiri",
                font_size=22,
                bold=True,
                color=(0.1, 0.1, 0.1, 1),
                size_hint=(0.18, 1),
                halign="left",
                valign="middle"
            )
            lbl_title.bind(size=lbl_title.setter("text_size"))
            row.add_widget(lbl_title)

            lbl_det = Label(
                text=rtl(details_short),
                font_name="Amiri",
                font_size=20,
                color=(0.2, 0.2, 0.2, 1),
                size_hint=(0.40, 1),
                halign="left",
                valign="middle"
            )
            lbl_det.bind(size=lbl_det.setter("text_size"))
            row.add_widget(lbl_det)

            lbl_img = Label(
                text=rtl(os.path.basename(img_path)),
                font_name="Amiri",
                font_size=20,
                color=(0.2, 0.2, 0.2, 1),
                size_hint=(0.22, 1),
                halign="center",
                valign="middle"
            )
            lbl_img.bind(size=lbl_img.setter("text_size"))
            row.add_widget(lbl_img)

            btn_edit = KivyImage(
                source="assets/icons/pencil.png",
                size_hint=(None, None),
                size=(32, 32),
                allow_stretch=True
            )
            btn_edit.pos_hint = {"center_y": 0.5}
            btn_edit.bind(on_touch_down=lambda inst, touch, i=idx: self._on_ad_edit(inst, touch, i))
            row.add_widget(btn_edit)

            btn_del = KivyImage(
                source="assets/icons/trash.png",
                size_hint=(None, None),
                size=(32, 32),
                allow_stretch=True
            )
            btn_del.pos_hint = {"center_y": 0.5}
            btn_del.bind(on_touch_down=lambda inst, touch, i=idx: self._on_ad_delete(inst, touch, i))
            row.add_widget(btn_del)

            self.list_grid.add_widget(row)


    def _on_ad_edit(self, widget, touch, ad_index):
        if widget.collide_point(*touch.pos):
            self._open_ad_popup(editing=True, ad_index=ad_index)


    def _on_ad_delete(self, widget, touch, ad_index):
        if not widget.collide_point(*touch.pos):
            return

        content = BoxLayout(orientation="vertical", padding=20, spacing=20)
        lbl = Label(
            text=rtl("هل أنت متأكد أنك تريد حذف هذا الإعلان؟"),
            font_name="Amiri",
            font_size=20,
            color=(0.1, 0.1, 0.1, 1),
            halign="center",
            valign="middle"
        )
        lbl.bind(size=lbl.setter("text_size"))

        btns = BoxLayout(spacing=20, size_hint_y=None, height=56)
        yes = LabelButton(
            text=rtl("نعم"),
            font_name="Amiri",
            font_size=20,
            bold=True,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        with yes.canvas.before:
            Color(1, 0.2, 0.2, 1)
            yes.bg = RoundedRectangle(radius=[24], pos=yes.pos, size=yes.size)
        yes.bind(pos=lambda w, *_: setattr(yes.bg, "pos", w.pos))
        yes.bind(size=lambda w, *_: setattr(yes.bg, "size", w.size))

        no = LabelButton(
            text=rtl("إلغاء"),
            font_name="Amiri",
            font_size=20,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        with no.canvas.before:
            Color(0.6, 0.6, 0.6, 1)
            no.bg = RoundedRectangle(radius=[24], pos=no.pos, size=no.size)
        no.bind(pos=lambda w, *_: setattr(no.bg, "pos", w.pos))
        no.bind(size=lambda w, *_: setattr(no.bg, "size", w.size))

        btns.add_widget(yes)
        btns.add_widget(no)
        content.add_widget(lbl)
        content.add_widget(btns)

        popup = Popup(title="", content=content, size_hint=(0.7, 0.4), auto_dismiss=False)

        def confirm_delete(inst):
            try:
                with open(self.ads_file, "r+", encoding="utf-8") as f:
                    arr = json.load(f)
                    if 0 <= ad_index < len(arr):
                        arr.pop(ad_index)
                        f.seek(0)
                        f.truncate()
                        json.dump(arr, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            popup.dismiss()
            self.refresh_list()

        yes.bind(on_release=confirm_delete)
        no.bind(on_release=lambda inst: popup.dismiss())
        popup.open()


    def _open_ad_popup(self, editing=False, ad_index=None):
        title_txt = rtl("تعديل إعلان") if editing else rtl("إضافة إعلان جديد")
        popup = ModalView(size_hint=(0.9, 0.8), auto_dismiss=False)

        box = BoxLayout(orientation="vertical", padding=24, spacing=24)
        with box.canvas.before:
            Color(1, 1, 1, 1)
            box.bg = RoundedRectangle(radius=[24], pos=box.pos, size=box.size)
        box.bind(pos=lambda w, *_: setattr(box.bg, "pos", w.pos))
        box.bind(size=lambda w, *_: setattr(box.bg, "size", w.size))

        lbl_title = Label(
            text=title_txt,
            font_name="Amiri",
            font_size=26,
            bold=True,
            color=(0.03, 0.03, 0.03, 1),
            halign="center",
            valign="middle",
            size_hint=(1, None),
            height=56
        )
        lbl_title.bind(size=lbl_title.setter("text_size"))
        box.add_widget(lbl_title)

        inp_title = RtlTextInput(
            hint_text=rtl("عنوان الإعلان"),
            font_size=22,
            multiline=False,
            foreground_color=(0.1, 0.1, 0.1, 1),
            background_color=(0.95, 0.95, 0.95, 1),
            size_hint=(1, None),
            height=56
        )
        inp_details = RtlTextInput(
            hint_text=rtl("تفاصيل الإعلان (متعددة الأسطر)"),
            font_size=20,
            multiline=True,
            foreground_color=(0.1, 0.1, 0.1, 1),
            background_color=(0.95, 0.95, 0.95, 1),
            size_hint=(1, None),
            height=120
        )
        inp_link = RtlTextInput(
            hint_text=rtl("رابط الإعلان (URL أو mailto:)"),
            font_size=20,
            multiline=False,
            foreground_color=(0.1, 0.1, 0.1, 1),
            background_color=(0.95, 0.95, 0.95, 1),
            size_hint=(1, None),
            height=56
        )
        inp_img = RtlTextInput(
            hint_text=rtl("مسار صورة الإعلان (اضغط للاختيار)"),
            font_size=20,
            multiline=False,
            readonly=True,
            foreground_color=(0.1, 0.1, 0.1, 1),
            background_color=(0.95, 0.95, 0.95, 1),
            size_hint=(1, None),
            height=56
        )

        if editing and ad_index is not None:
            try:
                with open(self.ads_file, "r", encoding="utf-8") as f:
                    arr = json.load(f)
                    if 0 <= ad_index < len(arr):
                        item = arr[ad_index]
                        inp_title.original_text = item.get("title", "")
                        inp_title.text = rtl(inp_title.original_text)
                        inp_details.original_text = item.get("details", "")
                        inp_details.text = rtl(inp_details.original_text)
                        inp_link.original_text = item.get("link", "")
                        inp_link.text = rtl(inp_link.original_text)
                        inp_img.original_text = item.get("image", "")
                        inp_img.text = rtl(inp_img.original_text)
            except Exception:
                pass

        btn_select = LabelButton(
            text=rtl("🖼️ اختر صورة"),
            font_name="Amiri",
            font_size=20,
            bold=True,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        btn_select.size_hint = (1, None)
        btn_select.height = 56
        with btn_select.canvas.before:
            Color(0.2, 0.6, 1, 1)
            btn_select.bg = RoundedRectangle(radius=[24], pos=btn_select.pos, size=btn_select.size)
        btn_select.bind(pos=lambda w, *_: setattr(btn_select.bg, "pos", w.pos))
        btn_select.bind(size=lambda w, *_: setattr(btn_select.bg, "size", w.size))

        def open_filechooser(inst):
            chooser = FileChooserIconView(filters=["*.png", "*.jpg", "*.jpeg"], size_hint=(1, 1))
            popup_fc = Popup(title=rtl("اختر صورة الإعلان"), content=chooser, size_hint=(0.9, 0.9))

            def on_file_select(fc, selection, touch=None):
                if selection:
                    inp_img.original_text = selection[0]
                    inp_img.text = rtl(inp_img.original_text)
                    popup_fc.dismiss()

            chooser.bind(on_submit=lambda fc, sel, touch: on_file_select(fc, sel, touch))
            popup_fc.open()

        btn_select.bind(on_release=open_filechooser)

        box.add_widget(inp_title)
        box.add_widget(inp_details)
        box.add_widget(inp_link)
        box.add_widget(inp_img)
        box.add_widget(btn_select)

        btn_save = LabelButton(
            text=rtl("حفظ"),
            font_name="Amiri",
            font_size=20,
            bold=True,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        btn_save.size_hint = (1, None)
        btn_save.height = 56
        with btn_save.canvas.before:
            Color(0.2, 0.6, 1, 1)
            btn_save.bg = RoundedRectangle(radius=[24], pos=btn_save.pos, size=btn_save.size)
        btn_save.bind(pos=lambda w, *_: setattr(btn_save.bg, "pos", w.pos))
        btn_save.bind(size=lambda w, *_: setattr(btn_save.bg, "size", w.size))

        btn_cancel = LabelButton(
            text=rtl("إلغاء"),
            font_name="Amiri",
            font_size=20,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle"
        )
        btn_cancel.size_hint = (1, None)
        btn_cancel.height = 56
        with btn_cancel.canvas.before:
            Color(0.6, 0.6, 0.6, 1)
            btn_cancel.bg = RoundedRectangle(radius=[24], pos=btn_cancel.pos, size=btn_cancel.size)
        btn_cancel.bind(pos=lambda w, *_: setattr(btn_cancel.bg, "pos", w.pos))
        btn_cancel.bind(size=lambda w, *_: setattr(btn_cancel.bg, "size", w.size))

        btn_box = BoxLayout(orientation="horizontal", spacing=20, size_hint_y=None, height=56)
        btn_box.add_widget(btn_save)
        btn_box.add_widget(btn_cancel)
        box.add_widget(btn_box)

        popup.add_widget(box)

        def save_ad(inst):
            new_title   = inp_title.original_text.strip()
            new_details = inp_details.original_text.strip()
            new_link    = inp_link.original_text.strip()
            new_img     = inp_img.original_text.strip()
            if not (new_title and new_details and new_link and new_img):
                return
            try:
                with open(self.ads_file, "r+", encoding="utf-8") as f:
                    arr = json.load(f)
                    if editing and ad_index is not None and 0 <= ad_index < len(arr):
                        arr[ad_index] = {
                            "image": new_img,
                            "title": new_title,
                            "details": new_details,
                            "link": new_link
                        }
                    else:
                        arr.append({
                            "image": new_img,
                            "title": new_title,
                            "details": new_details,
                            "link": new_link
                        })
                    f.seek(0)
                    f.truncate()
                    json.dump(arr, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            popup.dismiss()
            self.refresh_list()

        btn_save.bind(on_release=save_ad)
        btn_cancel.bind(on_release=lambda inst: popup.dismiss())
        popup.open()

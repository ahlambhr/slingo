# screens/sign_match.py

import os
import json
import random
import tempfile
import subprocess

import arabic_reshaper
from bidi.algorithm import get_display

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.video import Video
from kivy.uix.widget import Widget

# ─── Register your Arabic font ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FONT_PATH = os.path.join(BASE_DIR, 'fonts', 'Amiri-Regular.ttf')
if not os.path.isfile(FONT_PATH):
    raise IOError(f"Arabic font not found at {FONT_PATH}")
LabelBase.register(name="Amiri", fn_regular=FONT_PATH)


def rtl(text: str) -> str:
    """
    Reshape an Arabic string for right-to-left display in Kivy.
    """
    return get_display(arabic_reshaper.reshape(text))


class IconButton(ButtonBehavior, KivyImage):
    """
    A tappable Image button (e.g. back arrow).
    """
    pass


class StyledButton(Button):
    """
    A Button with rounded corners, drop shadow, and border to look more modern.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Remove default Kivy background
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)

        # Define our default colors
        self._bg_default = (0.2, 0.6, 1, 1)      # Blue fill
        self._bg_pressed = (0.1, 0.5, 0.9, 1)    # Slightly darker on press
        self._border_color = (0.05, 0.05, 0.2, 1)  # Dark border
        self._shadow_color = (0, 0, 0, 0.2)      # Subtle black shadow

        with self.canvas.before:
            # 1) Shadow color + rectangle
            self._shadow_color_instr = Color(*self._shadow_color)
            self._shadow_rect = RoundedRectangle(
                pos=(self.x, self.y - 6),
                size=(self.width, self.height),
                radius=[24, 24, 24, 24]
            )

            # 2) Background color + rounded rect
            self._bg_color_instr = Color(*self._bg_default)
            self._bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[24, 24, 24, 24]
            )

            # 3) Border color + slightly inset rounded rect
            self._border_color_instr = Color(*self._border_color)
            self._border_rect = RoundedRectangle(
                pos=(self.x + 1, self.y + 1),
                size=(self.width - 2, self.height - 2),
                radius=[24, 24, 24, 24]
            )

        # Bind to update whenever the Button’s pos/size change
        self.bind(pos=self._update_graphics, size=self._update_graphics)
        # Bind to change color on press/release
        self.bind(state=self._on_state_change)

    def _update_graphics(self, *args):
        # Update shadow rectangle
        self._shadow_rect.pos = (self.x, self.y - 6)
        self._shadow_rect.size = (self.width, self.height)

        # Update background rectangle
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

        # Update border rectangle
        self._border_rect.pos = (self.x + 1, self.y + 1)
        self._border_rect.size = (self.width - 2, self.height - 2)

    def _on_state_change(self, instance, value):
        if value == 'down':
            self._bg_color_instr.rgba = self._bg_pressed
        else:
            self._bg_color_instr.rgba = self._bg_default


class SignMatchScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ─── Background Color ───────────────────────────────────────────────
        with self.canvas.before:
            Color(0.96, 0.96, 1, 1)  # very light bluish‐white
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # ─── Load words from JSON ───────────────────────────────────────────
        self.video_dir = 'datavideos'
        self.img_dir = 'datapics'
        json_path = os.path.join(BASE_DIR, 'words.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            self.words = json.load(f)

        # Prepare question data
        self.questions = self._generate_questions()

        # Track score and index
        self.score = 0
        self.q_index = 0
        self.max_rounds = 10

        # Concatenate per-letter videos into a single MP4 per word
        self._tmp = tempfile.gettempdir()
        self._concat_map = {}
        self._prepare_all_word_videos()

        # ─── Root AnchorLayout (stuck to top) ───────────────────────────────
        anchor = AnchorLayout(anchor_x='center', anchor_y='top')
        self.add_widget(anchor)

        # ─── A Vertical BoxLayout inside the AnchorLayout ──────────────────
        # It should size itself to the sum of its children, not stretch vertically.
        root = BoxLayout(
            orientation='vertical',
            size_hint=(1, None),
            spacing=0
        )
        root.bind(minimum_height=root.setter('height'))
        anchor.add_widget(root)

        #
        # 1) ORANGE HEADER BAR
        #
        header = BoxLayout(size_hint_y=None, height=70)
        with header.canvas.before:
            Color(1, 0.5, 0.1, 1)  # bright orange
            self.header_rect = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda w, *_: setattr(self.header_rect, 'pos', w.pos))
        header.bind(size=lambda w, *_: setattr(self.header_rect, 'size', w.size))

        self.logo_label = Label(
            text="Slingo",
            font_name="Amiri",
            font_size=44,
            bold=True,
            color=(0.03, 0.05, 0.15, 1),
            halign='left',
            valign='middle',
            size_hint=(1, 1),
            padding=(20, 0),
        )
        self.logo_label.bind(size=self.logo_label.setter('text_size'))
        header.add_widget(self.logo_label)
        root.add_widget(header)

        # ─── Extra space below header ─────────────────────────────────────
        root.add_widget(Widget(size_hint_y=None, height=30))

        #
        # 2) BACK ARROW BUTTON (under header)
        #
        self.back_btn = IconButton(
            source="assets/icons/angle-double-left.png",
            size_hint=(None, None),
            size=(50, 50),
            allow_stretch=True,
        )
        back_anchor = AnchorLayout(
            size_hint_y=None, height=60, anchor_x='left', anchor_y='center'
        )
        back_anchor.add_widget(self.back_btn)
        root.add_widget(back_anchor)

        # ─── Add extra space after back arrow ─────────────────────────────
        root.add_widget(Widget(size_hint_y=None, height=30))

        #
        # 3) STEP BAR (10 segments, orange for completed, grey for pending)
        #
        self.step_container = BoxLayout(
            size_hint_y=None, height=20, padding=(20, 0), spacing=5
        )
        self.step_boxes = []
        for i in range(self.max_rounds):
            box = FloatLayout(size_hint_x=1)
            with box.canvas.before:
                if i < self.q_index:
                    c = Color(1, 0.5, 0.1, 1)  # orange = completed
                else:
                    c = Color(0.8, 0.8, 0.8, 1)  # grey = pending
                rect = Rectangle(pos=box.pos, size=box.size)
            box.step_color = c
            box.step_rect = rect
            box.bind(pos=lambda w, *_: setattr(w.step_rect, 'pos', w.pos))
            box.bind(size=lambda w, *_: setattr(w.step_rect, 'size', w.size))
            self.step_boxes.append(box)
            self.step_container.add_widget(box)
        root.add_widget(self.step_container)

        # ─── Extra space below step bar ───────────────────────────────────
        root.add_widget(Widget(size_hint_y=None, height=30))

        #
        # 4) MAIN QUESTION TEXT
        #
        question_box = BoxLayout(
            orientation='vertical', size_hint_y=None, height=100, padding=10, spacing=5
        )
        self.main_question = Label(
            text=rtl("ماذا تمثل هذه الإشارة!"),
            font_name="Amiri",
            font_size=30,
            bold=True,
            color=(0.15, 0.15, 0.15, 1),
            halign='center',
            valign='middle',
            size_hint_y=None,
            height=40,
        )
        self.main_question.bind(size=self.main_question.setter('text_size'))
        question_box.add_widget(self.main_question)

        self.sub_question = Label(
            text=rtl("اختر الصورة التي تناسب الإشارة"),
            font_name="Amiri",
            font_size=24,
            color=(0.5, 0.5, 0.5, 1),
            halign='center',
            valign='middle',
            size_hint_y=None,
            height=40,
        )
        self.sub_question.bind(size=self.sub_question.setter('text_size'))
        question_box.add_widget(self.sub_question)
        root.add_widget(question_box)

        # ─── Extra space before video ─────────────────────────────────────
        root.add_widget(Widget(size_hint_y=None, height=40))

        #
        # 5) VIDEO CARD (ROUNDED CORNERS + SHADOW)
        #
        video_anchor = AnchorLayout(size_hint_y=None, height=300, padding=10)
        video_card = FloatLayout(size_hint=(0.9, 1))
        with video_card.canvas.before:
            Color(0, 0, 0, 0.18)  # subtle shadow
            self.video_shadow = RoundedRectangle(
                pos=(video_card.x + 5, video_card.y - 5),
                size=(video_card.width, video_card.height),
                radius=[20, 20, 20, 20],
            )
            Color(1, 1, 1, 1)  # white background
            self.video_bg = RoundedRectangle(
                pos=video_card.pos,
                size=video_card.size,
                radius=[20, 20, 20, 20],
            )
            Color(0.85, 0.85, 0.85, 1)  # grey border
            self.video_border = RoundedRectangle(
                pos=(video_card.x + 2, video_card.y + 2),
                size=(video_card.width - 4, video_card.height - 4),
                radius=[20, 20, 20, 20],
            )
        video_card.bind(
            pos=lambda w, *_: (
                setattr(self.video_bg, 'pos', w.pos),
                setattr(self.video_shadow, 'pos', (w.x + 5, w.y - 5)),
                setattr(self.video_border, 'pos', (w.x + 2, w.y + 2)),
            )
        )
        video_card.bind(
            size=lambda w, *_: (
                setattr(self.video_bg, 'size', w.size),
                setattr(self.video_shadow, 'size', w.size),
                setattr(self.video_border, 'size', (w.width - 4, w.height - 4)),
            )
        )

        self.video = Video(
            source='',
            state='stop',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        # Auto‐loop video after a 2s delay
        self.video.bind(eos=self._on_eos_loop)

        video_card.add_widget(self.video)
        video_anchor.add_widget(video_card)
        root.add_widget(video_anchor)

        # ─── Extra space before option images ─────────────────────────────
        root.add_widget(Widget(size_hint_y=None, height=40))

        #
        # 6) OPTION CARDS (3 IMAGES SIDE BY SIDE)
        #
        self.opts_container = BoxLayout(
            orientation='horizontal',
            spacing=10,
            size_hint_y=None,
            height=240,
            padding=10
        )
        root.add_widget(self.opts_container)

        self.option_cards = []
        self.selected_card = None
        self.selected_key = None

        # The actual image buttons will be filled in next_question()

        # ─── Extra space before action area ──────────────────────────────
        root.add_widget(Widget(size_hint_y=None, height=40))

        #
        # 7) ACTION AREA: [StyledButton “تحقّق”] → [Feedback Bar] → [StyledButton “التالي”]
        #
        action_box = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=200,
            padding=10,
            spacing=20
        )
        # (a) “تحقّق” Button
        self.check_btn = StyledButton(
            text=rtl("تحقّق"),
            font_name="Amiri",
            font_size=26,
            bold=True,
            size_hint_y=None,
            height=70,
            on_press=self._on_check
        )
        self.check_btn.opacity = 0
        self.check_btn.disabled = True
        action_box.add_widget(self.check_btn)

        # (b) Feedback Bar (green if correct, red if wrong)
        self.feedback_bar = BoxLayout(
            size_hint_y=None,
            height=60,
            padding=10
        )
        with self.feedback_bar.canvas.before:
            self.feedback_color = Color(0, 0.6, 0, 1)  # default green
            self.feedback_rect = RoundedRectangle(
                pos=self.feedback_bar.pos,
                size=self.feedback_bar.size,
                radius=[12, 12, 12, 12]
            )
        self.feedback_bar.bind(
            pos=lambda w, *_: setattr(self.feedback_rect, 'pos', w.pos),
            size=lambda w, *_: setattr(self.feedback_rect, 'size', w.size),
        )
        self.feedback_label = Label(
            text="",
            font_name="Amiri",
            font_size=24,
            bold=True,
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle'
        )
        self.feedback_label.bind(size=self.feedback_label.setter('text_size'))
        self.feedback_bar.add_widget(self.feedback_label)
        self.feedback_bar.opacity = 0
        self.feedback_bar.disabled = True
        action_box.add_widget(self.feedback_bar)

        # (c) “التالي” Button
        self.next_btn = StyledButton(
            text=rtl("التالي"),
            font_name="Amiri",
            font_size=26,
            bold=True,
            size_hint_y=None,
            height=70,
            on_press=self._on_next
        )
        self.next_btn.opacity = 0
        self.next_btn.disabled = True
        action_box.add_widget(self.next_btn)

        root.add_widget(action_box)

        # ─── Finally, start first question ───────────────────────────────
        Clock.schedule_once(self.next_question, 0)

    def on_parent(self, instance, parent):
        if parent:
            # Bind back arrow to return to “home” screen
            self.back_btn.bind(on_release=lambda *_: setattr(parent, 'current', 'home'))

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _generate_questions(self):
        """
        Build a list of question dictionaries, each containing:
          - 'word': the Arabic word string (e.g. "بيت")
          - 'sequence': list of per-letter video filenames (e.g. ["ب.mp4","ي.mp4","ت.mp4"])
          - 'options': list of 3 image filenames (1 correct + 2 random wrong), shuffled
          - 'answer': the correct image filename
        """
        questions = []
        for item in self.words:
            word = item['word']
            answer_img = item['image']
            sequence = [f"{char}.mp4" for char in word]

            # pick 2 random wrong images
            wrong = [w['image'] for w in self.words if w['image'] != answer_img]
            random.shuffle(wrong)
            opts = [answer_img] + wrong[:2]
            random.shuffle(opts)

            questions.append({
                'word': word,
                'sequence': sequence,
                'options': opts,
                'answer': answer_img
            })
        return questions

    def _prepare_all_word_videos(self):
        """
        For each question, concatenate its per-letter videos into a single MP4
        in the temp folder. Store path in self._concat_map[word].
        """
        for q in self.questions:
            word = q['word']
            seq = q['sequence']
            out_mp4 = os.path.join(self._tmp, f"{word}.mp4")
            list_txt = os.path.join(self._tmp, f"{word}_list.txt")

            if not os.path.exists(out_mp4):
                with open(list_txt, 'w', encoding='utf-8') as f:
                    for clip in seq:
                        full = os.path.abspath(os.path.join(self.video_dir, clip)).replace('\\', '/')
                        f.write(f"file '{full}'\n")

                subprocess.run([
                    'ffmpeg', '-y',
                    '-f', 'concat', '-safe', '0',
                    '-i', list_txt,
                    '-c', 'copy',
                    out_mp4
                ], check=True)

            self._concat_map[word] = out_mp4

    def next_question(self, dt=None):
        """
        Advance to the next question (or show game over if done).
        """
        # 1) Reset action area: hide Check, Feedback, Next
        self.check_btn.opacity = 0
        self.check_btn.disabled = True
        self.feedback_bar.opacity = 0
        self.feedback_bar.disabled = True
        self.next_btn.opacity = 0
        self.next_btn.disabled = True

        # 2) Update step bar colors
        for i, box in enumerate(self.step_boxes):
            if i < self.q_index:
                box.step_color.rgba = (1, 0.5, 0.1, 1)  # orange
            else:
                box.step_color.rgba = (0.8, 0.8, 0.8, 1)  # grey

        # 3) If we’ve reached max_rounds, show the final “game over” popup
        if self.q_index >= self.max_rounds:
            return self._show_game_over()

        # 4) Clear old images and prepare for new
        self.opts_container.clear_widgets()
        self.option_cards = []
        self.selected_card = None
        self.selected_key = None

        # 5) Pick a random question
        self.current = random.choice(self.questions)

        # *** Shuffle again so the correct image is not always in the same place ***
        random.shuffle(self.current['options'])

        # 6) Create three equal‐width cards for each option image
        for img_file in self.current['options']:
            card = BoxLayout(size_hint_x=1)
            with card.canvas.before:
                # Drop shadow behind each card
                Color(0, 0, 0, 0.18)
                shadow = RoundedRectangle(
                    pos=(card.x + 5, card.y - 5),
                    size=(card.width, card.height),
                    radius=[15, 15, 15, 15]
                )
                # White background
                Color(1, 1, 1, 1)
                bg = RoundedRectangle(
                    pos=card.pos,
                    size=card.size,
                    radius=[15, 15, 15, 15]
                )
                # Grey border
                Color(0.85, 0.85, 0.85, 1)
                border = RoundedRectangle(
                    pos=(card.x + 2, card.y + 2),
                    size=(card.width - 4, card.height - 4),
                    radius=[15, 15, 15, 15]
                )
            card.shadow_rect = shadow
            card.bg_rect = bg
            card.border_rect = border
            card.border_color = card.canvas.before.children[0]

            card.bind(pos=lambda w, *_: setattr(w.shadow_rect, 'pos', (w.x + 5, w.y - 5)))
            card.bind(pos=lambda w, *_: setattr(w.bg_rect, 'pos', w.pos))
            card.bind(pos=lambda w, *_: setattr(w.border_rect, 'pos', (w.x + 2, w.y + 2)))
            card.bind(size=lambda w, *_: setattr(w.shadow_rect, 'size', w.size))
            card.bind(size=lambda w, *_: setattr(w.bg_rect, 'size', w.size))
            card.bind(size=lambda w, *_: setattr(w.border_rect, 'size', (w.width - 4, w.height - 4)))

            btn = Button(
                background_normal=os.path.join(self.img_dir, img_file),
                background_down=os.path.join(self.img_dir, img_file),
                size_hint=(1, 1),
                on_press=self._on_select
            )
            btn.answer_key = img_file
            card.add_widget(btn)
            self.opts_container.add_widget(card)
            self.option_cards.append((card, btn))

        # 7) Play (and auto‐loop) the concatenated video
        self.video.source = self._concat_map[self.current['word']]
        self.video.state = 'play'

    def _on_select(self, btn):
        """
        When an image is tapped, highlight its card’s border in blue, enable “تحقّق.”
        """
        # Un-highlight all others
        for card, b in self.option_cards:
            if b != btn:
                card.border_color.rgba = (0.85, 0.85, 0.85, 1)
        # Highlight the tapped card
        for card, b in self.option_cards:
            if b == btn:
                self.selected_card = card
                self.selected_key = b.answer_key
                card.border_color.rgba = (0.2, 0.6, 1, 1)  # bright blue

        # Show the “تحقّق” button
        self.check_btn.opacity = 1
        self.check_btn.disabled = False

    def _on_check(self, instance):
        """
        User pressed “تحقّق.” Show green or red feedback, then reveal “التالي.”
        """
        if not self.selected_key:
            return
        correct = (self.selected_key == self.current['answer'])
        if correct:
            self.score += 1
            self.feedback_color.rgba = (0, 0.6, 0, 1)  # green
            self.feedback_label.text = rtl("صحيح ✓")
        else:
            self.feedback_color.rgba = (0.8, 0, 0, 1)  # red
            self.feedback_label.text = rtl("خطأ ✗")

        self.feedback_bar.opacity = 1
        self.feedback_bar.disabled = False
        self.check_btn.opacity = 0
        self.check_btn.disabled = True

        self.next_btn.opacity = 1
        self.next_btn.disabled = False

    def _on_next(self, instance):
        """
        Advance to the next question.
        """
        self.q_index += 1
        self.next_question()

    def _on_eos_loop(self, instance, value):
        """
        Called when video EOS reached. Wait 2 seconds, then replay.
        """
        Clock.schedule_once(lambda dt: setattr(instance, 'state', 'play'), 2)

    def _show_game_over(self):
        """
        Show a modern, light‐background popup with final score and “ابدأ مرة أخرى.”
        """
        raw = f"انتهت اللعبة!\nنتيجتك: {self.score} من {self.max_rounds}"
        text = get_display(arabic_reshaper.reshape(raw))

        # Build a white, rounded-corner popup with a subtle border/shadow effect.
        content = BoxLayout(orientation='vertical', padding=20, spacing=20)
        with content.canvas.before:
            Color(1, 1, 1, 1)  # white background
            self.popup_bg = RoundedRectangle(
                pos=content.pos,
                size=content.size,
                radius=[20, 20, 20, 20]
            )
            # We rely on the OS window’s drop shadow, so we skip an explicit shadow here.

        content.bind(pos=lambda w, *_: setattr(self.popup_bg, 'pos', w.pos))
        content.bind(size=lambda w, *_: setattr(self.popup_bg, 'size', w.size))

        lbl = Label(
            text=text,
            font_name='Amiri',
            font_size='24sp',
            color=(0.1, 0.1, 0.1, 1),  # dark grey text
            halign='center',
            valign='middle'
        )
        lbl.bind(size=lbl.setter('text_size'))
        content.add_widget(lbl)

        btn = StyledButton(
            text=rtl("ابدأ مرة أخرى"),
            font_name="Amiri",
            font_size=26,
            bold=True,
            size_hint_y=None,
            height=70,
        )

        def restart(_):
            popup.dismiss()
            self.score = 0
            self.q_index = 0
            self.next_question()

        btn.bind(on_press=restart)
        content.add_widget(btn)

        popup = Popup(
            title='',
            content=content,
            size_hint=(0.8, 0.5),
            background='',  # no default popup background
        )
        popup.open()

    def back_to_home(self, instance):
        self.manager.current = "home"

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _nav_open_image(self):
        # If you ever want to jump to your predictor, you could do:
        # self.manager.current = 'predictor'
        pass

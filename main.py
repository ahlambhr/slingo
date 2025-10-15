from kivy.config import Config
Config.set('input', 'wm_pen', '')

from kivy.uix.screenmanager import ScreenManager
from kivymd.app import MDApp
from screens.home import HomeScreen
from screens.translator import TranslatorScreen
from screens.predictor import PredictorScreen
from screens.sign_match import SignMatchScreen  # if exists
from screens.login_screen import LoginScreen
from screens.register_screen import RegisterScreen
from screens.admin_dashboard import DashboardScreen
from kivy.core.text import LabelBase
from kivy.core.window import Window
Window.size = (360, 640)  # typical mobile screen size (width x height)

LabelBase.register(
    name="Amiri",
    fn_regular="fonts/Amiri-Regular.ttf"
)
class SlingoApp(MDApp):
    def build(self):
        self.title = "Slingo"
        self.theme_cls.primary_palette = "Orange"
        self.theme_cls.theme_style = "Light"  # or "Dark"
        
        # ✅ Apply to all labels
        self.theme_cls.font_family = "Amiri"
        self.theme_cls.font_styles["Button"] = ["Amiri", 16, True, -0.1]
        self.theme_cls.font_styles["Body1"] = ["Amiri", 16, False, 0]
        self.theme_cls.font_styles["H5"] = ["Amiri", 22, True, -1.1]

        sm = ScreenManager()

        # ✅ Add screens
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(RegisterScreen(name="register"))
        sm.add_widget(TranslatorScreen(name="translator"))
        sm.add_widget(PredictorScreen(name="predictor"))
        sm.add_widget(SignMatchScreen(name="sign_match"))  # only if you’ve defined it
        sm.add_widget(DashboardScreen(name="admin_dashboard"))

        print("✅ Screens added")
        sm.current = "login"  # Start from login screen
        print("✅ Current screen is set to:", sm.current)

        return sm
     # ✅ Used in KV files for shaping Arabic text
    def reshaped_text(self, text):
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))

if __name__ == "__main__":
    SlingoApp().run()

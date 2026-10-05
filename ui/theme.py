"""全局主题颜色体系：深色/浅色两套，QSS 模板生成 + 自绘组件读取"""
import string


DARK = {
    'bg_main': '#101420',
    'bg_shadow': '#0f111c',
    'bg_panel': '#161a2b',
    'bg_input': '#0e1322',
    'bg_card': '#191f32',
    'bg_card_border': '#3c4663',
    'bg_btn': '#2a324b',
    'bg_btn_alt': '#222a40',
    'bg_btn_hover': '#384260',
    'bg_select': '#2f3854',
    'bg_icon_bar': '#181c2c',
    'bg_icon_bar_hover': '#272e48',
    'bg_icon_bar_checked': '#2b3350',
    'bg_title_bar': '#101420',
    'bg_title_btn_hover': '#2c3352',
    'bg_menu': '#1a1e2e',
    'border': '#3c4663',
    'text': '#e8e9f2',
    'text_label': '#dddddd',
    'text_status': '#bbbbbb',
    'text_muted': '#9aa3c0',
    'text_hover': '#d6b162',
    'text_title': '#e6c47c',
    'text_accent': '#e2c382',
    'text_sub': '#e8cd8c',
    'accent_gold': '#d6b162',
    'select_green': '#3a5a2a',
    'scrollbar': '#4a5270',
    'scrollbar_hover': '#5a6280',
    'close_hover': '#b83030',
    'line_number': '#3c4663',
    'line_number_bg': '#0e1322',
    'highlight_yellow': '#ffe870',
    'progress_green': '#00ff00',
    'countdown_red': '#dc3c3c',
    'manual_green': '#4caf50',
    'manual_green_dark': '#388e3c',
    'toggle_bg': '#2d323c',
    'toggle_border': '#505666',
    'toggle_slider': '#4285f4',
    'toggle_text_off': '#a0a0a0',
}


LIGHT = {
    'bg_main': '#f5f6f8',
    'bg_shadow': '#e8ecf2',
    'bg_panel': '#ffffff',
    'bg_input': '#ffffff',
    'bg_card': '#ffffff',
    'bg_card_border': '#c4cad8',
    'bg_btn': '#e8ecf4',
    'bg_btn_alt': '#dde2ec',
    'bg_btn_hover': '#d8dee8',
    'bg_select': '#c8d4e8',
    'bg_icon_bar': '#e8ecf2',
    'bg_icon_bar_hover': '#d8dee8',
    'bg_icon_bar_checked': '#c8d4e8',
    'bg_title_bar': '#e8ecf2',
    'bg_title_btn_hover': '#d8dee8',
    'bg_menu': '#ffffff',
    'border': '#c4cad8',
    'text': '#2c3038',
    'text_label': '#4a5260',
    'text_status': '#6a7280',
    'text_muted': '#8a92a0',
    'text_hover': '#c0392b',
    'text_title': '#9a6e1a',
    'text_accent': '#8a6e2a',
    'text_sub': '#7a5e1a',
    'accent_gold': '#b8860b',
    'select_green': '#4a7a2a',
    'scrollbar': '#b0b8c8',
    'scrollbar_hover': '#9098a8',
    'close_hover': '#d83030',
    'line_number': '#8a92a0',
    'line_number_bg': '#f0f2f5',
    'highlight_yellow': '#ffe040',
    'progress_green': '#3cb371',
    'countdown_red': '#c0392b',
    'manual_green': '#4caf50',
    'manual_green_dark': '#388e3c',
    'toggle_bg': '#d8dee8',
    'toggle_border': '#b0b8c8',
    'toggle_slider': '#4285f4',
    'toggle_text_off': '#6a7280',
}


_THEMES = {'dark': DARK, 'light': LIGHT}
_current_name = 'dark'
_current = DARK


def set_theme(name):
    global _current_name, _current
    if name in _THEMES:
        _current_name = name
        _current = _THEMES[name]


def current_name():
    return _current_name


def is_light():
    return _current is LIGHT


def get(key):
    return _current[key]


def rgb(key):
    h = _current[key].lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


_QSS_TEMPLATE = string.Template("""QMainWindow{ background-color: $bg_main; }

QWidget#root_widget{ background-color: $bg_main; }

QWidget#content_widget{ background-color: $bg_main; }

QFrame#shadow_wrap{ background-color: $bg_shadow; border-radius: 0px; }

QLabel#card_title{ color:$text_title; font-size:16pt; font-weight:bold; }

QTextEdit{ background-color:$bg_input; border-radius:0px; border:1px solid $border; color:$text; padding:0px; }

QPushButton#top_tab{ background-color:$bg_btn_alt; color:$text_accent; border:1px solid $border; border-radius:8px; padding:8px 16px; font-size:11pt; }
QPushButton#top_tab:checked{ background-color:$bg_select; border:1px solid $border; }
QPushButton#top_tab:hover{ background-color:$bg_select; }

QPushButton#sub_btn{ background-color:$bg_btn; color:$text_sub; border:1px solid $border; border-radius:4px; padding:4px 10px; }
QPushButton#sub_btn:hover{ background-color:$bg_btn_hover; }

QPushButton#font_label{ background-color:$toggle_slider; color:#ffffff; border:1px solid $border; border-right:none; border-top-left-radius:4px; border-bottom-left-radius:4px; border-top-right-radius:0; border-bottom-right-radius:0; padding:2px 6px; margin-top:1px; }
QPushButton#font_label:hover{ background-color:$bg_btn_hover; }
QPushButton#dict_left{ background-color:$bg_btn; color:$text_sub; border:1px solid $border; border-right:none; border-top-left-radius:4px; border-bottom-left-radius:4px; border-top-right-radius:0; border-bottom-right-radius:0; padding:2px 6px; margin-top:1px; }
QPushButton#dict_left:checked{ background-color:$select_green; color:#ffffff; }
QPushButton#dict_left:hover{ background-color:$bg_btn_hover; }
QPushButton#dict_mid{ background-color:$bg_btn; color:$text_sub; border:1px solid $border; border-left:none; border-right:none; border-radius:0; padding:2px 6px; margin-top:1px; }
QPushButton#dict_mid:checked{ background-color:$select_green; color:#ffffff; }
QPushButton#dict_mid:hover{ background-color:$bg_btn_hover; }
QPushButton#dict_right{ background-color:$bg_btn; color:$text_sub; border:1px solid $border; border-top-right-radius:4px; border-bottom-right-radius:4px; border-top-left-radius:0; border-bottom-left-radius:0; padding:2px 6px; margin-top:1px; }
QPushButton#dict_right:hover{ background-color:$bg_btn_hover; }

QPushButton#dict_clear{ background-color:$bg_btn; color:$text_sub; border:1px solid $border; border-radius:4px; padding:2px 6px; margin-top:1px; }
QPushButton#dict_clear:hover{ background-color:$bg_btn_hover; }

QPushButton#icon_bar_btn{ background-color:$bg_icon_bar; color:$text_accent; border:none; padding:10px 4px; font-size:16pt; font-weight:bold; font-family: "KaiTi", "楷体", "STKaiti"; }
QPushButton#icon_bar_btn:hover{ background-color:$bg_icon_bar_hover; }
QPushButton#icon_bar_btn:checked{ border-left:3px solid $accent_gold; background-color:$bg_icon_bar_checked; }

QFrame#file_panel{ background-color:$bg_panel; border:1px solid $border; border-radius:8px; }
QTreeWidget{ background-color:$bg_panel; color:$text_label; border:none; }
QTreeWidget::item{ padding:4px 2px; }
QTreeWidget::item:selected{ background-color:$bg_select; }

QListWidget{ background-color:$bg_input; color:$text_label; border:1px solid $border; border-radius:4px; }
QListWidget::item{ padding:3px 8px; }
QListWidget::item:selected{ background-color:$bg_select; color:$text_title; }
QListWidget::item:hover{ background-color:$bg_icon_bar_hover; }

QLabel{ color:$text_label; }
QLabel#status_tip{ color:$text_status; }

QSplitter{ background-color: $bg_main; }
QSplitter::handle:horizontal{ background-color: $bg_main; border: none; width: 4px; margin: 0px; }

QScrollBar:vertical{ background-color: transparent; width: 3px; margin: 0px; border: none; }
QScrollBar::handle:vertical{ background-color: $scrollbar; min-height: 20px; border: none; border-radius: 1px; }
QScrollBar::handle:vertical:hover{ background-color: $scrollbar_hover; }
QScrollBar::add-line:vertical{ height: 0px; background: none; border: none; }
QScrollBar::sub-line:vertical{ height: 0px; background: none; border: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical{ background: none; border: none; }

QScrollBar:horizontal{ background-color: transparent; height: 3px; margin: 0px; border: none; }
QScrollBar::handle:horizontal{ background-color: $scrollbar; min-width: 20px; border: none; border-radius: 1px; }
QScrollBar::handle:horizontal:hover{ background-color: $scrollbar_hover; }
QScrollBar::add-line:horizontal{ width: 0px; background: none; border: none; }
QScrollBar::sub-line:horizontal{ width: 0px; background: none; border: none; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal{ background: none; border: none; }
""")


def qss():
    return _QSS_TEMPLATE.substitute(_current)
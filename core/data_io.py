import os
import json

DATA_FILE = "writing_train_data.json"
FONT_FILE = "writing_train_font.json"
THEME_FILE = "writing_train_theme.json"


def load_data():
    """读取全部数据，返回 dict；文件不存在或出错返回 None"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"数据加载失败: {e}")
    return None


def save_data(data):
    """全量写入数据文件"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("数据保存成功")
        return True
    except Exception as e:
        print(f"数据保存失败: {e}")
        return False


def load_font_str():
    """从独立小文件读取字体字符串，失败返回 None"""
    try:
        if os.path.exists(FONT_FILE):
            with open(FONT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('editor_font')
    except Exception as e:
        print(f"字体加载失败: {e}")
    return None


def save_font_str(font_str):
    """仅写入字体小文件，避免重写大数据文件"""
    try:
        with open(FONT_FILE, 'w', encoding='utf-8') as f:
            json.dump({'editor_font': font_str}, f, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"字体保存失败: {e}")
        return False


def load_theme_name():
    """读取主题名，失败返回 None"""
    try:
        if os.path.exists(THEME_FILE):
            with open(THEME_FILE, 'r', encoding='utf-8') as f:
                return json.load(f).get('theme')
    except Exception as e:
        print(f"主题加载失败: {e}")
    return None


def save_theme_name(name):
    """写入主题小文件"""
    try:
        with open(THEME_FILE, 'w', encoding='utf-8') as f:
            json.dump({'theme': name}, f, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"主题保存失败: {e}")
        return False
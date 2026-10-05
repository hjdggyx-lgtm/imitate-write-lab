from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QPushButton, QFrame, QTextEdit, QLabel, QTreeWidget, QTreeWidgetItem, QSplitter,
                             QSizePolicy, QButtonGroup, QListWidget, QListWidgetItem, QFileDialog, QMenu,
                             QFontDialog, QInputDialog, QStyledItemDelegate, QStyle,
                             QDialog, QSpinBox, QFormLayout)
from PyQt6.QtCore import QTimer, QPoint
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor, QPainter, QFont, QCursor
import re
import os
import json
import base64
from PyQt6.QtCore import Qt, QPoint, QObject, QRectF, QRect, QEvent, QEventLoop
from PyQt6.QtGui import QPainter, QPen, QColor, QPolygon, QMouseEvent, QRegion, QCursor
import sys

from ui.widgets import (OrnateCardFrame, LineNumberWidget, HighlightableTextEdit,
                        RoundItemDelegate, ProgressDelegate, CustomTitleBar, QtWidgetInspector,
                        SegmentedToggle)
from ui import theme
from core.data_io import (DATA_FILE, FONT_FILE, load_data, save_data,
                          load_font_str, save_font_str,
                          load_theme_name, save_theme_name)



class WindowResizer(QObject):
    """无边框窗口边缘拖拽调整大小：左/右/下/左下/右下"""
    EDGE = 6
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._edge = None
        self._press_rect = None
        self._press_pos = None
        self._cur_cursor = None
        QApplication.instance().installEventFilter(self)

    def _hit_edge(self, gp):
        if self.window.isMaximized():
            return None
        r = self.window.frameGeometry()
        x, y = gp.x(), gp.y()
        if not (r.left() - self.EDGE <= x <= r.right() + self.EDGE and
                r.top() - self.EDGE <= y <= r.bottom() + self.EDGE):
            return None
        left = abs(x - r.left()) <= self.EDGE
        right = abs(x - r.right()) <= self.EDGE
        bottom = abs(y - r.bottom()) <= self.EDGE
        parts = []
        if left:
            parts.append('L')
        if right:
            parts.append('R')
        if bottom:
            parts.append('B')
        return ''.join(parts) if parts else None

    def _cursor_for(self, edge):
        if edge in ('L', 'R'):
            return Qt.CursorShape.SizeHorCursor
        if edge == 'B':
            return Qt.CursorShape.SizeVerCursor
        if edge == 'LB':
            return Qt.CursorShape.SizeBDiagCursor
        if edge == 'RB':
            return Qt.CursorShape.SizeFDiagCursor
        return None

    def eventFilter(self, obj, event):
        t = event.type()
        if t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            gp = event.globalPosition().toPoint()
            edge = self._hit_edge(gp)
            if edge:
                self._edge = edge
                self._press_rect = self.window.geometry()
                self._press_pos = gp
                return True
        elif t == QEvent.Type.MouseMove:
            gp = event.globalPosition().toPoint()
            if self._edge:
                self._do_resize(gp)
                return True
            edge = self._hit_edge(gp)
            cur = self._cursor_for(edge) if edge else None
            if cur != self._cur_cursor:
                if self._cur_cursor is not None:
                    QApplication.restoreOverrideCursor()
                if cur is not None:
                    QApplication.setOverrideCursor(QCursor(cur))
                self._cur_cursor = cur
        elif t == QEvent.Type.MouseButtonRelease and self._edge:
            self._edge = None
            self._press_rect = None
            self._press_pos = None
            return True
        return False

    def _do_resize(self, gp):
        r = self._press_rect
        dx = gp.x() - self._press_pos.x()
        dy = gp.y() - self._press_pos.y()
        new = QRect(r)
        if 'L' in self._edge:
            new.setLeft(r.left() + dx)
        if 'R' in self._edge:
            new.setRight(r.right() + dx)
        if 'B' in self._edge:
            new.setBottom(r.bottom() + dy)
        min_w = max(self.window.minimumWidth(), 400)
        min_h = max(self.window.minimumHeight(), 300)
        if new.width() < min_w:
            if 'L' in self._edge:
                new.setLeft(new.right() - min_w + 1)
            else:
                new.setRight(new.left() + min_w - 1)
        if new.height() < min_h:
            new.setBottom(new.top() + min_h - 1)
        self.window.setGeometry(new)


class WritingTrainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 防抖定时器：删行后延迟补占位空行，避免频繁触发
        self.pad_timer = QTimer(self)
        self.pad_timer.setSingleShot(True)
        self.pad_timer.timeout.connect(self._ensure_write_not_shorter)
        self._auto_align = True  # 复写区自动对齐原文开关
        # 开启无边框，使用自定义标题栏
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(1700, 950)
        self.setMinimumSize(400, 300)
        _t = load_theme_name()
        if _t:
            theme.set_theme(_t)
        self.setStyleSheet(theme.qss())

        root_widget = QWidget()
        root_widget.setObjectName("root_widget")
        root_layout = QVBoxLayout(root_widget)
        root_layout.setContentsMargins(0,0,0,0)
        root_layout.setSpacing(0)

        # 自定义标题栏放在最顶部
        self.title_bar = CustomTitleBar(self)
        root_layout.addWidget(self.title_bar)



        # 原本全部UI内容放到标题栏下方
        content_widget = QWidget()
        content_widget.setObjectName("content_widget")
        outer_h = QHBoxLayout(content_widget)
        outer_h.setContentsMargins(0,0,0,6)
        outer_h.setSpacing(0)

        # ---------------------- 1.最左侧图标竖工具栏 ----------------------
        icon_bar = QFrame()
        icon_bar.setFixedWidth(48)
        icon_layout = QVBoxLayout(icon_bar)
        icon_layout.setContentsMargins(0,8,0,8)
        icon_layout.setSpacing(2)

        icon_texts = ["练","写","资","评","图","记"]
        self.icon_bar_group = QButtonGroup(self)
        self.icon_bar_group.setExclusive(True)
        self.icon_buttons = []
        for i, txt in enumerate(icon_texts):
            b = QPushButton(txt)
            b.setObjectName("icon_bar_btn")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.icon_bar_group.addButton(b, i)
            icon_layout.addWidget(b)
            self.icon_buttons.append(b)
        icon_layout.addStretch(1)
        outer_h.addWidget(icon_bar)

        self.icon_buttons[0].setChecked(True)
        self.icon_bar_group.idClicked.connect(self.on_icon_bar_switch)

        # 章节记忆存储：记录每本书最后选中的章节
        self.novel_chapter_memory = {}

        # 复写区内容记忆：按 "小说名||章节名" 保存每章节复写内容
        self.chapter_write_memory = {}

        # 小说数据存储：存储导入的小说文件和章节信息
        self.novel_data = {}  # {小说名: {file_path: str, chapters: {章节名: 内容}}}

        # 最后打开的小说和章节
        self.last_opened_novel = None
        self.last_opened_chapter = None

        # 启动时加载数据
        QTimer.singleShot(100, self.load_app_data)

        # ---------------------- 2.文件树面板 + 主区域，分割器拖拽宽度 ----------------------
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter = splitter
        splitter.setHandleWidth(4)
        splitter.setChildrenCollapsible(False)

        # 文件树面板
        file_panel = QFrame()
        file_panel.setObjectName("file_panel")
        file_panel.setMinimumWidth(220)
        file_panel.setMaximumWidth(320)
        file_layout = QVBoxLayout(file_panel)
        file_layout.setContentsMargins(0,3,0,4)
        file_layout.setSpacing(3)

        # 标题行：左边是标题，右边是导入按钮
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0,0,0,0)
        title_row.setSpacing(0)

        lbl_file_title = QLabel("资源管理器")
        lbl_file_title.setStyleSheet("font-size:13pt; font-weight:bold; padding:4px;")
        title_row.addWidget(lbl_file_title)

        title_row.addStretch(1)  # 添加弹性空间，把导入按钮推到右端

        btn_import = QPushButton("导入")
        self.btn_import = btn_import
        self._style_import_btn()
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.clicked.connect(self.on_import_novel)
        title_row.addWidget(btn_import)

        file_layout.addLayout(title_row)

        # 标题下分隔线
        sep_title = QFrame()
        self.sep_title = sep_title
        sep_title.setFrameShape(QFrame.Shape.HLine)
        sep_title.setFixedHeight(1)
        sep_title.setStyleSheet(f"background-color:{theme.get('border')}; border:none;")
        file_layout.addWidget(sep_title)

        # 创建一个内部容器来容纳小说列表和章节列表
        inner_container = QWidget()
        inner_layout = QVBoxLayout(inner_container)
        inner_layout.setContentsMargins(0,0,0,0)
        inner_layout.setSpacing(3)

        # 上部分：小说列表
        self.novel_list = QListWidget()
        self.novel_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.novel_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.novel_list.customContextMenuRequested.connect(self.show_novel_context_menu)
        self.novel_list.setStyleSheet(self._list_style())
        self.novel_list.setSpacing(2)
        self.novel_list.setItemDelegate(RoundItemDelegate())
        self.novel_list.setMouseTracking(True)
        self.novel_list.viewport().setMouseTracking(True)
        self.novel_list.viewport().installEventFilter(self)
        self.novel_list.setMaximumHeight(150)
        inner_layout.addWidget(self.novel_list)

        # 分隔线
        separator = QFrame()
        self.separator = separator
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color:{theme.get('border')}; border:none;")
        inner_layout.addWidget(separator)

        # 下部分：章节列表
        self.chapter_list = QListWidget()
        self.chapter_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.chapter_list.setStyleSheet(self._list_style())
        self.chapter_list.setSpacing(2)
        self.chapter_list.setItemDelegate(ProgressDelegate(self))
        self.chapter_list.setMouseTracking(True)
        self.chapter_list.viewport().setMouseTracking(True)
        self.chapter_list.viewport().installEventFilter(self)
        self.chapter_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner_layout.addWidget(self.chapter_list)

        file_layout.addWidget(inner_container)

        # 连接选择事件
        self.novel_list.itemClicked.connect(self.on_novel_selected)
        self.chapter_list.itemClicked.connect(self.on_chapter_selected)

        # 防止信号循环的标志
        self._is_changing_novel = False

        splitter.addWidget(file_panel)

        # ---------------------- 3.主内容区：顶部按钮 + 左右双卡片 + 底部状态栏 ----------------------
        self.main_area = QWidget()
        main_layout = QVBoxLayout(self.main_area)
        main_layout.setContentsMargins(0,0,5,0)
        main_layout.setSpacing(12)


        # 原文区、复写区双卡片
        h_card_layout = QHBoxLayout()
        h_card_layout.setSpacing(4)

        # 原文卡片
        shadow_left = QFrame()
        shadow_left.setObjectName("shadow_wrap")
        lay_shadow_left = QVBoxLayout(shadow_left)
        lay_shadow_left.setContentsMargins(0,0,0,0)

        card_left = OrnateCardFrame()
        lay_left = QVBoxLayout(card_left)
        lay_left.setSpacing(5)
        lay_left.setContentsMargins(3, 5, 3, 4)


        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        title_left = QLabel("原文区")
        title_left.setObjectName("card_title")
        title_left.setStyleSheet("margin-left:6px;")
        title_left.setFixedHeight(26)
        title_row.addWidget(title_left)

        # 字体连体按钮（字体 | 当前字体名+字号）
        self.btn_font = QPushButton("字体")
        self.btn_font.setObjectName("font_label")
        self.btn_font.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_font.setFixedHeight(26)
        self.btn_font.clicked.connect(self.on_font_button)
        self.btn_font_name = QPushButton("字体")
        self.btn_font_name.setObjectName("dict_right")
        self.btn_font_name.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_font_name.setFixedHeight(26)
        self.btn_font_name.clicked.connect(self.on_font_button)
        font_container = QWidget()
        font_row = QHBoxLayout(font_container)
        font_row.setContentsMargins(0, 0, 0, 0)
        font_row.setSpacing(0)
        font_row.addWidget(self.btn_font)
        font_row.addWidget(self.btn_font_name)
        f = QFont(self.font())
        f.setPointSize(11)
        self.btn_font.setFont(f)
        self.btn_font_name.setFont(f)
        title_row.addWidget(font_container)

        self.btn_mode_toggle = SegmentedToggle(["抄写", "默写"])

        self.btn_mode_toggle.toggled.connect(self.on_dictation_toggle)

        self.btn_dictation = QPushButton("默写手动模式")
        self.btn_dictation.setObjectName("dict_left")
        self.btn_dictation.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_dictation.clicked.connect(self.on_dictation_mode_toggle)
        self.btn_dictation.setEnabled(False)
        self.btn_dictation.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dictation.setFixedHeight(22)
        _f = QFont(self.font()); _f.setPointSize(11); self.btn_dictation.setFont(_f)

        self.btn_dictation_time = QPushButton("设置")
        self.btn_dictation_time.setObjectName("dict_right")
        self.btn_dictation_time.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_dictation_time.clicked.connect(self.on_dictation_set_time)
        self.btn_dictation_time.setEnabled(False)
        self.btn_dictation_time.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dictation_time.setFixedHeight(22)
        _f2 = QFont(self.font()); _f2.setPointSize(11); self.btn_dictation_time.setFont(_f2)

        dictation_sub = QHBoxLayout()
        dictation_sub.setSpacing(0)
        dictation_sub.setContentsMargins(0, 0, 0, 0)
        dictation_sub.addWidget(self.btn_dictation)
        dictation_sub.addWidget(self.btn_dictation_time)

        dictation_group = QHBoxLayout()
        dictation_group.setSpacing(6)
        dictation_group.setContentsMargins(0, 0, 0, 0)
        switch_wrap = QWidget()
        switch_wrap.setFixedHeight(26)
        sw_l = QHBoxLayout(switch_wrap)
        sw_l.setContentsMargins(0, 0, 0, 0)
        sw_l.addWidget(self.btn_mode_toggle, 0, Qt.AlignmentFlag.AlignBottom)
        dictation_group.addWidget(switch_wrap)
        dictation_group.addLayout(dictation_sub)
        title_row.addLayout(dictation_group)

        title_row.addStretch()
        lay_left.addLayout(title_row)

        self.text_original = HighlightableTextEdit()
        self.text_original.setPlaceholderText("此处放置参考原文...")
        self.text_original.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 去掉横向滚动条

        # 原文区行号显示
        self.original_line_numbers = LineNumberWidget(self.text_original)
        original_container = QWidget()
        original_layout = QHBoxLayout(original_container)
        original_layout.setContentsMargins(0, 0, 0, 0)
        original_layout.setSpacing(0)
        original_layout.addWidget(self.original_line_numbers)
        original_layout.addWidget(self.text_original)

        lay_left.addWidget(original_container)

        status_row_left = QHBoxLayout()
        status_row_left.setContentsMargins(6, 0, 6, 0)
        status_row_left.setSpacing(8)
        self.status_line_left = QLabel("第1行")
        self.status_line_left.setStyleSheet(f"color:{theme.get('text_muted')}; font-size:9pt;")
        self.status_count_left = QLabel("0/0字")
        self.status_count_left.setStyleSheet(f"color:{theme.get('text_muted')}; font-size:9pt;")
        status_row_left.addStretch()
        status_row_left.addWidget(self.status_line_left)
        status_row_left.addWidget(self.status_count_left)
        lay_left.addLayout(status_row_left)
        self.text_original.cursorPositionChanged.connect(self.update_original_status)
        self.text_original.textChanged.connect(self.update_original_status)
        self.update_original_status()


        lay_shadow_left.addWidget(card_left)
        h_card_layout.addWidget(shadow_left, stretch=1)

        # 复写卡片
        shadow_right = QFrame()
        shadow_right.setObjectName("shadow_wrap")
        lay_shadow_right = QVBoxLayout(shadow_right)
        lay_shadow_right.setContentsMargins(0,0,0,0)

        card_right = OrnateCardFrame()
        lay_right = QVBoxLayout(card_right)
        lay_right.setSpacing(5)
        lay_right.setContentsMargins(3, 5, 3, 4)


        title_right = QLabel("复写区")
        title_right.setObjectName("card_title")
        title_right.setStyleSheet("margin-left:4px;")
        title_row_right = QHBoxLayout()
        title_row_right.setSpacing(6)
        title_row_right.addWidget(title_right, 0, Qt.AlignmentFlag.AlignVCenter)
        btn_clear_write = QPushButton("清屏")
        btn_clear_write.setObjectName("dict_clear")
        btn_clear_write.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_clear_write.clicked.connect(self.on_clear_write)
        btn_clear_write.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear_write.setFixedHeight(22)
        _f4 = QFont(self.font()); _f4.setPointSize(11); btn_clear_write.setFont(_f4)
        title_row_right.addWidget(btn_clear_write, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_auto_align = QPushButton("自动对齐原文(关)")
        self.btn_auto_align.setObjectName("dict_clear")
        self.btn_auto_align.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_auto_align.clicked.connect(self.on_auto_align_toggle)
        self.btn_auto_align.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_auto_align.setFixedHeight(22)
        _f3 = QFont(self.font()); _f3.setPointSize(11); self.btn_auto_align.setFont(_f3)
        title_row_right.addWidget(self.btn_auto_align, 0, Qt.AlignmentFlag.AlignVCenter)

        title_row_right.addStretch()
        lay_right.addLayout(title_row_right)

        self.text_write = HighlightableTextEdit()
        self.text_write.setPlaceholderText("请在此处复写内容...")
        self.text_write.cursorPositionChanged.connect(self.on_write_cursor_changed)
        self.text_write.installEventFilter(self)
        self.text_write.viewport().installEventFilter(self)
        self.text_write.viewport().setMouseTracking(True)
        self.text_write.setMouseTracking(True)
        self.text_write.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 去掉横向滚动条

        # 复写区行号显示
        self.write_line_numbers = LineNumberWidget(self.text_write, reference_edit=self.text_original)
        write_container = QWidget()
        write_layout = QHBoxLayout(write_container)
        write_layout.setContentsMargins(0, 0, 0, 0)
        write_layout.setSpacing(0)
        write_layout.addWidget(self.write_line_numbers)
        write_layout.addWidget(self.text_write)

        lay_right.addWidget(write_container)

        status_row_right = QHBoxLayout()
        status_row_right.setContentsMargins(6, 0, 6, 0)
        status_row_right.setSpacing(8)
        self.status_line_right = QLabel("第1行")
        self.status_line_right.setStyleSheet(f"color:{theme.get('text_muted')}; font-size:9pt;")
        self.status_count_right = QLabel("0/0字")
        self.status_count_right.setStyleSheet(f"color:{theme.get('text_muted')}; font-size:9pt;")
        status_row_right.addStretch()
        status_row_right.addWidget(self.status_line_right)
        status_row_right.addWidget(self.status_count_right)
        lay_right.addLayout(status_row_right)
        self.text_write.cursorPositionChanged.connect(self.update_write_status)
        self.text_write.textChanged.connect(self.update_write_status)
        self.text_write.textChanged.connect(self.on_write_text_changed)
        self.text_original.verticalScrollBar().valueChanged.connect(self._sync_write_from_original)
        self.update_write_status()


        lay_shadow_right.addWidget(card_right)
        h_card_layout.addWidget(shadow_right, stretch=1)

        main_layout.addLayout(h_card_layout, stretch=1)


        splitter.addWidget(self.main_area)
        splitter.setStretchFactor(1,1)

        outer_h.addWidget(splitter)

        root_layout.addWidget(content_widget)
        self.setCentralWidget(root_widget)

        # 默写模式状态
        self._dictation_enabled = False
        self._dictation_auto = False  # False=手动模式, True=自动模式
        self._dictation_time_table = [3, 5, 8, 12, 15, 18, 20]  # ≤5/6-10/11-20/21-30/31-40/41-50/>50字
        self._dictation_active = False
        self._dictation_timer = QTimer(self)
        self._dictation_timer.setSingleShot(True)
        self._dictation_timer.timeout.connect(self._on_dictation_timeout)
        self._dictation_countdown = 0
        self._dictation_countdown_timer = QTimer(self)
        self._dictation_countdown_timer.setSingleShot(False)
        self._dictation_countdown_timer.timeout.connect(self._on_countdown_tick)

        # 初始默认字体（QSS 已去掉 font-size，字号由 setFont 控制）
        default_font = QFont(QApplication.font())
        if default_font.pointSize() <= 0:
            default_font.setPointSize(11)
        self.apply_editor_font(default_font)

        self._resizer = WindowResizer(self)

        if __debug__:
            self._inspector = QtWidgetInspector(self)

    def closeEvent(self, event):
        """窗口关闭时保存数据"""
        self.save_app_data()
        event.accept()

    def load_app_data(self):
        """加载应用数据"""
        font_from_small = self._load_font_only()
        data = load_data()
        if data is None:
            print("未找到数据文件，使用默认设置")
            return
        try:
            # 恢复窗口位置和大小
            if 'window_geometry' in data:
                from PyQt6.QtCore import QByteArray
                geometry_str = data['window_geometry']
                geometry = QByteArray.fromHex(geometry_str.encode())
                self.restoreGeometry(geometry)

            # 恢复小说数据
            if 'novel_data' in data:
                self.novel_data = data['novel_data']
                # 重新填充小说列表
                self.novel_list.clear()
                for novel_name in self.novel_data.keys():
                    self.novel_list.addItem(novel_name)

            # 恢复章节记忆
            if 'novel_chapter_memory' in data:
                self.novel_chapter_memory = data['novel_chapter_memory']

            # 恢复复写区内容记忆
            if 'chapter_write_memory' in data:
                self.chapter_write_memory = data['chapter_write_memory']

            # 恢复编辑器字体（小文件优先，回退到数据文件内字段）
            if font_from_small is not None:
                self.apply_editor_font(font_from_small)
            elif 'editor_font' in data:
                f = QFont()
                if f.fromString(data['editor_font']):
                    self.apply_editor_font(f)

            # 恢复默写分档秒数
            if 'dictation_time_table' in data:
                t = data['dictation_time_table']
                if len(t) >= 7:
                    self._dictation_time_table = t[:7]
                elif len(t) == 5:
                    self._dictation_time_table = [t[0], t[1], t[2], t[2], t[3], t[3], t[4]]
            elif 'dictation_seconds' in data:
                self._dictation_time_table = [3, 5, 8, 12, data['dictation_seconds'], 18, 20]

            # 恢复最后打开的小说和章节
            if 'last_opened_novel' in data:
                self.last_opened_novel = data['last_opened_novel']
            if 'last_opened_chapter' in data:
                self.last_opened_chapter = data['last_opened_chapter']

            # 恢复最后打开的章节
            if self.last_opened_novel and self.last_opened_novel in self.novel_data:
                # 找到并选中最后打开的小说
                items = self.novel_list.findItems(self.last_opened_novel, Qt.MatchFlag.MatchExactly)
                if items:
                    self.novel_list.setCurrentItem(items[0])
                    # 触发小说选择事件来加载章节
                    self.on_novel_selected(items[0])

            print("数据加载成功")
        except Exception as e:
            print(f"数据加载失败: {e}")

    def save_app_data(self):
        """保存应用数据"""
        geometry = self.saveGeometry()
        geometry_str = bytes(geometry).hex()
        data = {
            'window_geometry': geometry_str,
            'novel_data': self.novel_data,
            'novel_chapter_memory': self.novel_chapter_memory,
            'chapter_write_memory': self.chapter_write_memory,
            'last_opened_novel': self.last_opened_novel,
            'last_opened_chapter': self.last_opened_chapter,
            'editor_font': self.text_original.font().toString(),
            'dictation_time_table': self._dictation_time_table
        }
        save_data(data)

    def _save_font_only(self):
        """仅保存编辑器字体到独立小文件，避免重写大数据文件"""
        save_font_str(self.text_original.font().toString())

    def _load_font_only(self):
        """从独立小文件读取字体，成功返回 QFont，否则返回 None"""
        font_str = load_font_str()
        if font_str:
            fnt = QFont()
            if fnt.fromString(font_str):
                return fnt
        return None

    def on_icon_bar_switch(self, btn_id):
        if btn_id == 0:
            self.main_area.show()
            return
        self.main_area.show()

    def on_import_novel(self):
        """导入小说文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择小说文件",
            "",
            "文本文件 (*.txt);;所有文件 (*)"
        )

        if file_path:
            try:
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 解析章节
                chapters = self.parse_chapters(content)

                if not chapters:
                    print("未找到章节，使用整个文件作为一个章节")
                    chapters = {"全文": content}

                # 获取小说名称（使用文件名）
                novel_name = os.path.splitext(os.path.basename(file_path))[0]

                # 存储小说数据
                self.novel_data[novel_name] = {
                    'file_path': file_path,
                    'chapters': chapters
                }

                # 添加到小说列表
                self.novel_list.addItem(novel_name)

                print(f"成功导入小说: {novel_name}, 章节数: {len(chapters)}")

            except Exception as e:
                print(f"导入小说失败: {e}")

    def show_novel_context_menu(self, position):
        """显示小说列表右键菜单"""
        item = self.novel_list.itemAt(position)
        if item:
            novel_name = item.text()

            menu = QMenu()
            menu.setStyleSheet(f"""
                QMenu{{
                    background-color:{theme.get('bg_menu')};
                    border:1px solid {theme.get('border')};
                    color:{theme.get('text')};
                }}
                QMenu::item{{
                    padding:5px 20px;
                }}
                QMenu::item:selected{{
                    background-color:{theme.get('bg_select')};
                }}
            """)
            delete_action = menu.addAction("删除")

            action = menu.exec(self.novel_list.mapToGlobal(position))

            if action == delete_action:
                self.delete_novel(novel_name)

    def delete_novel(self, novel_name):
        """删除小说"""
        try:
            # 从数据中删除
            if novel_name in self.novel_data:
                del self.novel_data[novel_name]

            # 从章节记忆中删除
            if novel_name in self.novel_chapter_memory:
                del self.novel_chapter_memory[novel_name]

            # 如果删除的是最后打开的小说，清除记录
            if self.last_opened_novel == novel_name:
                self.last_opened_novel = None
                self.last_opened_chapter = None

            # 从列表中删除
            items = self.novel_list.findItems(novel_name, Qt.MatchFlag.MatchExactly)
            for item in items:
                self.novel_list.takeItem(self.novel_list.row(item))

            # 清空章节列表和原文区
            self.chapter_list.clear()
            self.text_original.clear()

            print(f"已完全删除小说: {novel_name}（包括所有相关记录）")

        except Exception as e:
            print(f"删除小说失败: {e}")

    def parse_chapters(self, content):
        """解析小说章节"""
        chapters = {}

        # 简单有效的章节标题正则表达式
        chapter_patterns = [
            r'第[0-9零一二三四五六七八九十百千万]+章[^\n]{0,30}',  # 第X章 + 章节名
            r'第[0-9零一二三四五六七八九十百千万]+节[^\n]{0,30}',  # 第X节 + 章节名
            r'第[0-9零一二三四五六七八九十百千万]+回[^\n]{0,30}',  # 第X回 + 章节名
            r'Chapter\s*[0-9IVX]+[^\n]{0,30}',  # Chapter X + 章节名
            r'卷[一二三四五六七八九十百千万]+[^\n]{0,30}',  # 卷X + 章节名
        ]

        # 合并所有模式
        combined_pattern = '|'.join(f'({pattern})' for pattern in chapter_patterns)

        # 查找所有章节标题
        matches = list(re.finditer(combined_pattern, content, re.IGNORECASE))

        if not matches:
            return {}

        # 去重并过滤无效章节
        seen_titles = set()
        valid_matches = []

        for match in matches:
            chapter_title = match.group().strip()

            # 过滤掉明显无效的章节标题（只过滤书名号，不过滤括号）
            if any(char in chapter_title for char in ['《', '》', '.com', 'http']):
                continue

            # 去重
            if chapter_title not in seen_titles:
                seen_titles.add(chapter_title)
                valid_matches.append(match)

        if not valid_matches:
            return {}

        # 提取章节内容
        for i, match in enumerate(valid_matches):
            chapter_title = match.group().strip()
            start_pos = match.start()

            # 确定章节结束位置
            if i + 1 < len(valid_matches):
                end_pos = valid_matches[i + 1].start()
            else:
                end_pos = len(content)

            chapter_content = content[start_pos:end_pos].strip()

            # 清理章节内容：去掉标题行，只保留正文
            lines = chapter_content.split('\n')
            # 找到第一个非标题行
            content_start = 0
            for j, line in enumerate(lines):
                if line.strip() and not re.match(combined_pattern, line, re.IGNORECASE):
                    content_start = j
                    break

            if content_start > 0:
                chapter_content = '\n'.join(lines[content_start:]).strip()

            # 确保章节内容不为空
            if chapter_content:
                chapters[chapter_title] = chapter_content

        return chapters

    def on_novel_selected(self, item):
        """当选中小说时更新章节列表"""
        novel_name = item.text()

        # 防止重复触发
        if self._is_changing_novel:
            return

        self._is_changing_novel = True

        # 清空章节列表
        self.chapter_list.clear()

        # 从导入的数据中获取章节
        if novel_name in self.novel_data:
            chapters = self.novel_data[novel_name]['chapters']
            for chapter_title in chapters.keys():
                self.chapter_list.addItem(chapter_title)
        else:
            print(f"未找到小说数据: {novel_name}")
            self._is_changing_novel = False
            return

        # 章节记忆逻辑
        target_chapter = None
        try:
            if novel_name in self.novel_chapter_memory:
                # 如果这本书之前选过章节，则选中之前选中的章节
                remembered_chapter = self.novel_chapter_memory[novel_name]
                items = self.chapter_list.findItems(remembered_chapter, Qt.MatchFlag.MatchExactly)
                if items:
                    target_chapter = items[0]
            else:
                # 如果这本书没选过章节，默认选中第一章
                if self.chapter_list.count() > 0:
                    target_chapter = self.chapter_list.item(0)
        except Exception as e:
            print(f"章节记忆逻辑出错: {e}")
            # 出错时默认选中第一章
            if self.chapter_list.count() > 0:
                target_chapter = self.chapter_list.item(0)

        if target_chapter:
            self.chapter_list.setCurrentItem(target_chapter)
            # 通过章节选中恢复原文 + 复写区记忆内容
            self.on_chapter_selected(target_chapter)

        self._is_changing_novel = False

    def on_chapter_selected(self, item):
        """当选中章节时显示内容到原文区"""
        try:
            chapter_title = item.text()
            # 获取当前选中的小说
            selected_novel_items = self.novel_list.selectedItems()
            if not selected_novel_items:
                return

            novel_name = selected_novel_items[0].text()

            # 记忆当前选中的章节
            self.novel_chapter_memory[novel_name] = chapter_title

            # 记录最后打开的小说和章节
            self.last_opened_novel = novel_name
            self.last_opened_chapter = chapter_title

            print(f"记住章节: {novel_name} -> {chapter_title}")

            chapter_content = self.get_chapter_content(novel_name, chapter_title)

            # 显示到原文区（段首半角空格归一化为全角空格，保证任意字体下段首缩进恒为2个中文字宽）
            self.text_original.setText(self._normalize_paragraph_indent(chapter_content))

            # 恢复该章节的复写区内容
            key = f"{novel_name}||{chapter_title}"
            # 先剥掉旧 memory 残留的尾部占位空行，再由 _pad 按原文行数重新补
            self.text_write.setText(self.chapter_write_memory.get(key, "").rstrip('\n'))
            self._pad_write_to_original()

            # 初始化高亮
            self.highlight_original_lines(1)
        except Exception as e:
            print(f"章节选择出错: {e}")

    def on_write_text_changed(self):
        """复写区内容变化时，记忆到当前章节"""
        print("[on_write_text_changed] 复写区内容改变")
        if self.last_opened_novel and self.last_opened_chapter:
            key = f"{self.last_opened_novel}||{self.last_opened_chapter}"
            # 只存纯内容（去掉尾部占位空行），避免占位被持久化成残留
            self.chapter_write_memory[key] = self.text_write.toPlainText().rstrip('\n')
            self.chapter_list.viewport().update()
        QTimer.singleShot(0, self._auto_scroll)
        print("[防抖] 启动 pad_timer")
        self.pad_timer.start(120)

    def _auto_scroll(self):
        """复写区写到2/3时，原文区与复写区同步上滚；原文区到底则复写区停滚"""
        write_edit = self.text_write
        cursor = write_edit.textCursor()
        cur_line = self.get_visual_line_number(cursor) + 1  # 1-based 视觉行，与原文高亮同基准
        orig_edit = self.text_original
        doc = orig_edit.document()
        doc_layout = doc.documentLayout()
        visual = 0
        target_y = None
        block = doc.begin()
        while block.isValid():
            bl = block.layout()
            if bl is not None:
                n = bl.lineCount()
                if n == 0:
                    n = 1
                for i in range(n):
                    visual += 1
                    if visual == cur_line:
                        line = bl.lineAt(i)
                        target_y = doc_layout.blockBoundingRect(block).y() + line.y()
                        break
            if target_y is not None:
                break
            block = block.next()
        if target_y is None:
            return
        vp_h_orig = orig_edit.viewport().height()
        sb_orig = orig_edit.verticalScrollBar()
        new_orig = int(target_y - vp_h_orig * 0.6)
        new_orig = max(0, min(new_orig, sb_orig.maximum()))
        orig_at_bottom = new_orig >= sb_orig.maximum()
        # 临时断开同步，避免原文滚动反向把复写区设两次值
        sb_orig.valueChanged.disconnect(self._sync_write_from_original)
        sb_orig.setValue(new_orig)
        sb_orig.valueChanged.connect(self._sync_write_from_original)
        if orig_at_bottom:
            return
        # 复写区：光标行超过2/3则上滚锚定2/3（用文档坐标，避免 cursorRect 临界不触发）
        w_block = cursor.block()
        w_bl = w_block.layout()
        if w_bl is not None:
            w_pos_in_block = cursor.position() - w_block.position()
            w_line = w_bl.lineForTextPosition(w_pos_in_block)
            if w_line.isValid():
                cursor_doc_y = write_edit.document().documentLayout().blockBoundingRect(w_block).y() + w_line.y()
                scroll_y = write_edit.verticalScrollBar().value()
                vp_h = write_edit.viewport().height()
                threshold = vp_h * 0.6
                # 开启时把光标行锚定到 2/3 对齐原文；关闭时复写区不动，保留手动位置
                if self._auto_align:
                    write_edit.verticalScrollBar().setValue(int(cursor_doc_y - threshold))

    def on_clear_write(self):
        """清空复写区"""
        self.text_write.clear()
        self._pad_write_to_original()

    def on_auto_align_toggle(self):
        """切换复写区自动对齐原文开关"""
        self._auto_align = not self._auto_align
        state = "关" if self._auto_align else "开"
        self.btn_auto_align.setText(f"自动对齐原文({state})")
        print(f"[自动对齐] {state}")
        if self._auto_align:
            QTimer.singleShot(0, self._auto_scroll)

    def _visual_line_count(self, widget):
        """统计视觉行数；layout 未就绪返回 None，上层放弃对齐"""
        doc = widget.document()
        total = 0
        block = doc.firstBlock()
        while block.isValid():
            layout = block.layout()
            if layout is None:
                print(f"【_visual_line_count警告】block {block.blockNumber()} layout=None，统计失效")
                return None
            total += layout.lineCount()
            block = block.next()
        return total

    def _pad_write_to_original(self):
        """强制复写区视觉行数=原文区：删尾部多余空行或补占位空行"""
        vp_o = self.text_original.viewport().width()
        vp_w = self.text_write.viewport().width()
        if vp_o > 0:
            self.text_original.document().setTextWidth(vp_o)
        if vp_w > 0:
            self.text_write.document().setTextWidth(vp_w)
        QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)  # setTextWidth 触发布局，处理完再统计
        orig_lines = self._visual_line_count(self.text_original)
        write_lines = self._visual_line_count(self.text_write)
        if orig_lines is None or write_lines is None:
            print("[_pad] 视觉行数统计失败，放弃对齐")
            return
        if write_lines == orig_lines:
            return
        self.text_write.blockSignals(True)
        try:
            if write_lines > orig_lines:
                doc = self.text_write.document()
                while True:
                    cur = self._visual_line_count(self.text_write)
                    if cur is None or cur <= orig_lines:
                        break
                    last = doc.lastBlock()
                    if last.text() != "" or last == doc.begin():
                        break
                    QTextCursor(last).deletePreviousChar()
            else:
                self.text_write.setPlainText(
                    self.text_write.toPlainText() + '\n' * (orig_lines - write_lines)
                )
        finally:
            self.text_write.blockSignals(False)

    def _sync_write_from_original(self, val):
        """原文区手动滚动时，复写区按比例同步跟随（适应两边文档高度差异）"""
        sb_o = self.text_original.verticalScrollBar()
        sb_w = self.text_write.verticalScrollBar()
        max_o = sb_o.maximum()
        if max_o > 0:
            sb_w.setValue(int(val / max_o * sb_w.maximum()))
        else:
            sb_w.setValue(0)

    def _trim_tail_empty_line(self):
        """删掉复写区最后一个空行（占位），与刚按的回车抵消，维持总行数=原文行数"""
        doc = self.text_write.document()
        last_block = doc.lastBlock()
        # 只在最后一个 block 是空行、且文档不止一个 block 时删
        if last_block.text() != "" or last_block == doc.begin():
            return
        cursor = QTextCursor(last_block)
        cursor.deletePreviousChar()

    def _trim_two_tail_lines(self):
        """删掉复写区尾部两个空行（占位），与回车插入的 \\n\\n 抵消"""
        self._trim_tail_empty_line()
        self._trim_tail_empty_line()

    def _ensure_write_not_shorter(self):
        """复写区视觉行数少于原文时，在末尾补占位空行（删行后自动补齐），不动光标"""
        if getattr(self, '_in_ensure', False):
            print("[防抖到期] 重入保护，跳过")
            return
        self._in_ensure = True
        try:
            print("[防抖到期] 调用 _ensure_write_not_shorter")
            self.pad_timer.stop()
            vp_o = self.text_original.viewport().width()
            vp_w = self.text_write.viewport().width()
            if vp_o > 0:
                self.text_original.document().setTextWidth(vp_o)
            if vp_w > 0:
                self.text_write.document().setTextWidth(vp_w)
            QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
            orig_lines = self._visual_line_count(self.text_original)
            write_lines = self._visual_line_count(self.text_write)
            if orig_lines is None or write_lines is None:
                print("[对齐] 视觉行数统计失败，放弃")
                return
            print(f"[对齐诊断] 原文视觉行:{orig_lines} 复写视觉行:{write_lines}")
            if write_lines == orig_lines:
                print("[对齐] 无需调整")
                return
            if write_lines > orig_lines:
                # 复写区比原文多：删尾部多余占位空行
                print(f"[对齐] 复写多{write_lines - orig_lines}行，删尾部占位")
                doc = self.text_write.document()
                self.text_write.blockSignals(True)
                try:
                    while True:
                        cur = self._visual_line_count(self.text_write)
                        if cur is None or cur <= orig_lines:
                            break
                        last = doc.lastBlock()
                        if last.text() != "" or last == doc.begin():
                            break
                        QTextCursor(last).deletePreviousChar()
                finally:
                    self.text_write.blockSignals(False)
                print("[对齐] 删多余占位完成")
                return
            # 复写区比原文少：补占位空行
            last = self.text_write.document().lastBlock()
            if last.text() != "":
                print("[对齐] 末尾非空行，缓冲池被破坏，跳过自动补齐")
                return
            need_add = orig_lines - write_lines
            print(f"[对齐] 需要补:{need_add}行")
            self.text_write.blockSignals(True)
            try:
                cursor = QTextCursor(self.text_write.document())
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertText('\n' * need_add)
            finally:
                self.text_write.blockSignals(False)
            print(f"[对齐] 补行完成，已追加{need_add}行")
        finally:
            self._in_ensure = False


    def on_dictation_toggle(self, index=None):
        """切换抄写/默写模式：0=抄写, 1=默写"""
        if index is None:
            index = 1 if not self._dictation_enabled else 0
        self._dictation_enabled = (index == 1)
        self.btn_dictation.setEnabled(self._dictation_enabled)
        self.btn_dictation_time.setEnabled(self._dictation_enabled)
        if not self._dictation_enabled:
            self._dictation_timer.stop()
            self._dictation_countdown_timer.stop()
            self.text_write._countdown_value = None
            self.text_write._manual_pending = False
            self.text_write.setReadOnly(False)
            self.text_write.viewport().update()
        self._restart_dictation_timer()

    def on_dictation_mode_toggle(self):
        """切换默写手动/自动模式"""
        self._dictation_auto = not self._dictation_auto
        self.btn_dictation.setText("默写自动模式" if self._dictation_auto else "默写手动模式")
        self._restart_dictation_timer()

    def on_dictation_set_time(self):
        """设置默写分档秒数：按高亮行字数分7档，每档秒数可调"""
        dlg = QDialog(self)
        dlg.setWindowTitle("默写显示时间设置")
        dlg.setStyleSheet(f"QDialog {{ background-color: {theme.get('bg_panel')}; }} QLabel {{ color: {theme.get('text')}; font-size: 13px; }} QPushButton {{ background-color: {theme.get('bg_btn')}; color: {theme.get('text')}; padding: 4px 16px; border: none; border-radius: 3px; }} QPushButton:hover {{ background-color: {theme.get('bg_btn_hover')}; }} QSpinBox {{ background-color: {theme.get('bg_input')}; color: {theme.get('text')}; border: 1px solid {theme.get('border')}; border-radius: 3px; padding: 2px; }}")
        form = QFormLayout(dlg)
        labels = ["≤5字", "6-10字", "11-20字", "21-30字", "31-40字", "41-50字", ">50字"]
        spins = []
        for i, lab in enumerate(labels):
            lb = QLabel(lab)
            sp = QSpinBox()
            sp.setRange(1, 120)
            sp.setValue(self._dictation_time_table[i])
            sp.setSuffix(" 秒")
            form.addRow(lb, sp)
            spins.append(sp)
        btn_row = QHBoxLayout()
        btn_ok = QPushButton("确定", dlg)
        btn_cancel = QPushButton("取消", dlg)
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        form.addRow(btn_row)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._dictation_time_table = [sp.value() for sp in spins]
            self.save_app_data()
            self._restart_dictation_timer()

    def _get_highlight_char_count(self):
        """统计原文区高亮行的总字数"""
        hl = self.text_original._highlight_lines
        if not hl:
            return 0
        doc = self.text_original.document()
        block = doc.begin()
        visual_no = 0
        total = 0
        while block.isValid():
            bl = block.layout()
            if bl is not None:
                n = bl.lineCount()
                if n == 0:
                    n = 1
                block_text = block.text()
                for i in range(n):
                    if (visual_no + 1) in hl:
                        line = bl.lineAt(i)
                        tl = line.textLength()
                        if tl > 0:
                            ts = line.textStart()
                            total += len(block_text[ts:ts + tl])
                    visual_no += 1
            block = block.next()
        return total

    def _restart_dictation_timer(self):
        """有高亮且开启默写时，按高亮行字数查表算秒数，重置隐藏状态并启动倒计时"""
        self._dictation_active = False
        self.text_original._dictation_active = False
        self.text_original.viewport().update()
        self._dictation_countdown_timer.stop()
        if self._dictation_enabled and self.text_original._highlight_lines:
            chars = self._get_highlight_char_count()
            if chars <= 5:
                secs = self._dictation_time_table[0]
            elif chars <= 10:
                secs = self._dictation_time_table[1]
            elif chars <= 20:
                secs = self._dictation_time_table[2]
            elif chars <= 30:
                secs = self._dictation_time_table[3]
            elif chars <= 40:
                secs = self._dictation_time_table[4]
            elif chars <= 50:
                secs = self._dictation_time_table[5]
            else:
                secs = self._dictation_time_table[6]
            if __debug__:
                print(f"[默写] 高亮{chars}字 → {secs}秒")
            if self._dictation_auto:
                self._dictation_countdown = secs
                self.text_write._countdown_value = secs
                self.text_write._manual_pending = False
                self.text_write.setReadOnly(True)
                self.text_write.viewport().update()
                self._dictation_timer.start(secs * 1000)
                self._dictation_countdown_timer.start(1000)
            else:
                self.text_write._countdown_value = None
                self.text_write._manual_pending = True
                self.text_write.setReadOnly(True)
                self.text_write.viewport().update()
        else:
            self.text_write._countdown_value = None
            self.text_write._manual_pending = False
            self.text_write.setReadOnly(False)
            self.text_write.viewport().update()

    def _on_countdown_tick(self):
        """每秒刷新复写区倒计时遮罩数字"""
        self._dictation_countdown -= 1
        if self._dictation_countdown > 0:
            self.text_write._countdown_value = self._dictation_countdown
            self.text_write.viewport().update()
        else:
            self._dictation_countdown_timer.stop()
            self.text_write._countdown_value = None
            self.text_write.viewport().update()

    def _on_manual_confirmed(self):
        """手动模式点击'记住了'：隐藏高亮行文字，开始默写"""
        self.text_write._manual_pending = False
        self._dictation_active = True
        self.text_original._dictation_active = True
        self.text_original.viewport().update()
        self.text_write.setReadOnly(False)
        self.text_write.viewport().setCursor(QCursor(Qt.CursorShape.IBeamCursor))
        self.text_write.viewport().update()

    def _on_dictation_timeout(self):
        """倒计时到，隐藏高亮行文字"""
        self._dictation_active = True
        self.text_original._dictation_active = True
        self.text_original.viewport().update()
        self._dictation_countdown_timer.stop()
        self.text_write._countdown_value = None
        self.text_write.setReadOnly(False)
        self.text_write.viewport().update()

    def on_font_button(self):
        """字体按钮：弹窗选择字体，应用到原文区/复写区并保存"""
        current = self.text_original.font()
        font, ok = QFontDialog.getFont(current, self, "选择编辑器字体")
        if not ok:
            return
        self.apply_editor_font(font)
        self._save_font_only()

    def apply_editor_font(self, font):
        """把字体应用到两个编辑器并刷新行号/高亮"""
        self.text_original.setFont(font)
        self.text_write.setFont(font)
        self._update_font_button(font)
        QTimer.singleShot(0, self._refresh_after_font_change)

    def _update_font_button(self, font):
        """按钮显示 字体名(最多4字,超出加省略号)+字号，并用该字体渲染按钮文字"""
        name = font.family()
        name_part = name if len(name) <= 4 else name[:4] + "…"
        size = font.pointSize()
        if size <= 0:
            size = self.font().pointSize()
        self.btn_font_name.setText(f"{name_part}{size}")

    def _refresh_after_font_change(self):
        self.original_line_numbers.update()
        self.write_line_numbers.update()
        self.text_original.viewport().update()
        self.text_write.viewport().update()

    def on_write_cursor_changed(self):
        """复写区光标位置改变时更新原文区高亮"""
        try:
            cursor = self.text_write.textCursor()
            current_line = self.get_visual_line_number(cursor) + 1  # 1-based 视觉行
            if current_line < 1:
                current_line = 1
            targets = [current_line]  # 同行号高亮：复写第N行 → 原文第N行
            if __debug__:
                print(f"[光标] 复写视觉行={current_line} → 原文高亮视觉行={targets}")
            self.highlight_original_lines(targets)
            if current_line != getattr(self, '_last_dictation_line', None):
                self._last_dictation_line = current_line
                self._restart_dictation_timer()
            # 鼠标点击改光标后也同步上翻位置，不必等打字
            QTimer.singleShot(0, self._auto_scroll)
        except Exception as e:
            print(f"光标位置同步出错: {e}")

    def update_original_status(self):
        c = self.text_original.textCursor()
        line = self.get_visual_line_number(c) + 1
        if line < 1:
            line = 1
        pos = c.position()
        total = self.text_original.document().characterCount() - 1
        self.status_line_left.setText(f"第{line}行")
        self.status_count_left.setText(f"{pos}/{total}字")

    def update_write_status(self):
        c = self.text_write.textCursor()
        line = self.get_visual_line_number(c) + 1
        if line < 1:
            line = 1
        plain = self.text_write.toPlainText().rstrip('\n')
        total = len(plain)
        pos = min(c.position(), total)
        self.status_line_right.setText(f"第{line}行")
        self.status_count_right.setText(f"{pos}/{total}字")

    def _style_import_btn(self):
        self.btn_import.setStyleSheet(f"""
            QPushButton{{
                background-color:transparent;
                border:none;
                color:{theme.get('text_title')};
                font-size:10pt;
                padding:4px 8px;
            }}
            QPushButton:hover{{
                color:{theme.get('accent_gold')};
            }}
        """)

    def _list_style(self):
        return f"""
            QListWidget{{
                background-color:transparent;
                border:none;
                font-size:11pt;
                padding:0px;
                margin:0px;
            }}
            QListView{{
                background-color:transparent;
                border:none;
                padding:0px;
                margin:0px;
            }}
            QListView::item{{
                padding:0px;
                margin:0px;
                height:16px;
            }}
            QListView::item:selected{{
                background-color:{theme.get('bg_select')};
                border:none;
                outline:none;
            }}
        """

    def apply_theme(self, name):
        theme.set_theme(name)
        save_theme_name(name)
        self.setStyleSheet(theme.qss())
        self.title_bar.refresh_theme()
        self._style_import_btn()
        self.sep_title.setStyleSheet(f"background-color:{theme.get('border')}; border:none;")
        self.separator.setStyleSheet(f"background-color:{theme.get('border')}; border:none;")
        self.novel_list.setStyleSheet(self._list_style())
        self.chapter_list.setStyleSheet(self._list_style())
        muted = theme.get('text_muted')
        self.status_line_left.setStyleSheet(f"color:{muted}; font-size:9pt;")
        self.status_count_left.setStyleSheet(f"color:{muted}; font-size:9pt;")
        self.status_line_right.setStyleSheet(f"color:{muted}; font-size:9pt;")
        self.status_count_right.setStyleSheet(f"color:{muted}; font-size:9pt;")
        self.original_line_numbers.refresh_theme()
        self.write_line_numbers.refresh_theme()
        self.text_original.viewport().update()
        self.text_write.viewport().update()
        self.novel_list.viewport().update()
        self.chapter_list.viewport().update()

    def get_visual_line_number(self, cursor):
        """获取光标所在的真实视觉行号（0-based，基于 QTextLayout 视觉行）"""
        try:
            block = cursor.block()
            blk_layout = block.layout()
            if blk_layout is None:
                return 0
            pos_in_block = cursor.position() - block.position()
            line = blk_layout.lineForTextPosition(pos_in_block)
            line_in_block = line.lineNumber() if line.isValid() else 0
            visual = 0
            cur = cursor.document().begin()
            while cur.isValid() and cur != block:
                bl = cur.layout()
                if bl is not None:
                    n = bl.lineCount()
                    visual += n if n > 0 else 1
                cur = cur.next()
            visual += line_in_block
            return visual
        except Exception as e:
            print(f"计算视觉行号出错: {e}")
            return 0

    def eventFilter(self, obj, event):
        """事件过滤器，处理复写区的鼠标点击和回车键"""
        if obj is self.novel_list.viewport() or obj is self.chapter_list.viewport():
            if event.type() == event.Type.MouseMove:
                lst = self.novel_list if obj is self.novel_list.viewport() else self.chapter_list
                if lst.itemAt(event.position().toPoint()) is not None:
                    obj.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                else:
                    obj.unsetCursor()
            return False
        if obj == self.text_write or obj == self.text_write.viewport():
            if self.text_write._countdown_value is not None and self.text_write._countdown_value > 0:
                if event.type() == event.Type.KeyPress or event.type() == event.Type.MouseButtonPress:
                    return True
            if self.text_write._manual_pending:
                if event.type() == event.Type.MouseButtonPress:
                    self._on_manual_confirmed()
                    return True
                if event.type() == event.Type.KeyPress:
                    return True
                if event.type() == event.Type.MouseMove:
                    btn_rect = self.text_write._manual_btn_rect
                    if btn_rect is not None and btn_rect.contains(event.position()):
                        if not self.text_write._manual_btn_hover:
                            self.text_write._manual_btn_hover = True
                            self.text_write.viewport().setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                            self.text_write.viewport().update()
                    else:
                        if self.text_write._manual_btn_hover:
                            self.text_write._manual_btn_hover = False
                            self.text_write.viewport().setCursor(QCursor(Qt.CursorShape.IBeamCursor))
                            self.text_write.viewport().update()
                    return True
            if obj == self.text_write.viewport() and event.type() == event.Type.MouseButtonPress:
                QTimer.singleShot(0, self.on_write_cursor_changed)
            if obj == self.text_write and event.type() == event.Type.KeyPress and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                # 回车：先删尾部2行空行占位（此时尾部是空行能删），再插空行+缩进，净变化0维持总行数
                self._trim_two_tail_lines()
                cursor = self.text_write.textCursor()
                cursor.insertText("\n\n\u3000\u3000")
                self.text_write.setTextCursor(cursor)
                return True
        return super().eventFilter(obj, event)

    def on_write_focus_in(self, event):
        """复写区获得焦点时更新高亮"""
        try:
            # 获得焦点时立即更新高亮
            QTimer.singleShot(0, self.on_write_cursor_changed)
            # 调用原始的focusInEvent
            QTextEdit.focusInEvent(self.text_write, event)
        except Exception as e:
            print(f"焦点事件处理出错: {e}")

    def highlight_original_lines(self, line_numbers):
        """高亮原文区指定视觉行（1-based，可传单值或列表），自绘矩形方式"""
        try:
            if isinstance(line_numbers, int):
                line_numbers = [line_numbers]
            self.text_original.set_highlight_lines(line_numbers)

            # 滚动到第一个高亮行所在 block
            if not line_numbers:
                return
            doc = self.text_original.document()
            target = line_numbers[0] - 1  # 0-based
            if target < 0:
                return
            block = doc.begin()
            visual_no = 0
            while block.isValid():
                bl = block.layout()
                if bl is not None:
                    n = bl.lineCount()
                    if n == 0:
                        n = 1
                    if visual_no + n > target:
                        vis_cursor = QTextCursor(block)
                        self.text_original.setTextCursor(vis_cursor)
                        self.text_original.ensureCursorVisible()
                        break
                    visual_no += n
                block = block.next()
            if __debug__:
                print(f"[高亮] 视觉行={line_numbers}")
        except Exception as e:
            print(f"高亮原文行出错: {e}")

    def clear_highlights(self):
        """清除原文区的高亮"""
        self.text_original.set_highlight_lines([])

    def get_chapter_content(self, novel_name, chapter_title):
        """获取章节内容"""
        # 从导入的数据中获取章节内容
        if novel_name in self.novel_data:
            chapters = self.novel_data[novel_name]['chapters']
            return chapters.get(chapter_title, "暂无内容")
        else:
            return "暂无内容"

    @staticmethod
    def _normalize_paragraph_indent(text):
        """段首连续半角空格按 2:1 转为全角空格（4 半角 → 2 全角），
        全角空格/Tab 等其它缩进保持不变。保证任意字体下段首缩进恒为整数个中文字宽。"""
        if not text:
            return text
        lines = text.split('\n')
        for i, line in enumerate(lines):
            n = 0
            while n < len(line) and line[n] == ' ':
                n += 1
            if n > 0:
                full = n // 2
                rem = n % 2
                lines[i] = '\u3000' * full + ' ' * rem + line[n:]
        return '\n'.join(lines)

    def showEvent(self, event):
        super().showEvent(event)
        self.splitter.setSizes([260, 1000])
        event.accept()







if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = WritingTrainWindow()
    win.show()
    sys.exit(app.exec())

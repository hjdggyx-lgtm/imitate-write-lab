from PyQt6.QtWidgets import (QFrame, QWidget, QTextEdit, QPushButton, QLabel,
                             QHBoxLayout, QVBoxLayout, QDialog, QStyledItemDelegate, QStyle, QApplication)
from PyQt6.QtCore import (QTimer, Qt, QPoint, QObject, QRectF, QRect,
                          QPropertyAnimation, QEasingCurve, pyqtSignal, pyqtProperty)
from PyQt6.QtGui import QPainter, QPen, QColor, QPolygon, QMouseEvent, QRegion, QFont
from ui import theme


class OrnateCardFrame(QFrame):
    """卡片容器：圆角背景 + 细线边框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.radius = 8

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        bg = QColor(*theme.rgb('bg_card'))
        bd = QColor(*theme.rgb('bg_card_border'))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, self.radius, self.radius)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(bd, 1))
        painter.drawRoundedRect(rect, self.radius, self.radius)



class LineNumberWidget(QWidget):
    """行号显示控件 - Notepad3风格"""
    def __init__(self, text_edit, parent=None, reference_edit=None):
        super().__init__(parent)
        self.text_edit = text_edit
        self.reference_edit = reference_edit
        self.setFixedWidth(30)
        self.setStyleSheet(f"background-color:{theme.get('line_number_bg')}; border:none;")

        self.doc_layout = self.text_edit.document().documentLayout()

        self.text_edit.verticalScrollBar().valueChanged.connect(self.on_scroll_changed)
        self.text_edit.textChanged.connect(self.on_text_changed)
        self.text_edit.resizeEvent = self.on_resize_event
        if reference_edit is not None:
            reference_edit.textChanged.connect(self.on_text_changed)

    def on_scroll_changed(self, value):
        self.update()

    def on_text_changed(self):
        QTimer.singleShot(0, self.update)

    def on_resize_event(self, event):
        QTimer.singleShot(0, self.update)
        QTextEdit.resizeEvent(self.text_edit, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.text_edit.font())
        fm = painter.fontMetrics()
        ascent = fm.ascent()
        line_h = fm.height()

        scroll_y = self.text_edit.verticalScrollBar().value()
        painter.setPen(QColor(*theme.rgb('line_number')))

        doc = self.text_edit.document()
        doc_layout = doc.documentLayout()
        block = doc.begin()
        visual_no = 0
        widget_h = self.height()
        visible_count = 0
        last_screen_y = None

        while block.isValid():
            blk_layout = block.layout()
            if blk_layout is not None:
                top = doc_layout.blockBoundingRect(block).y()
                n = blk_layout.lineCount()
                if n == 0:
                    n = 1
                for i in range(n):
                    line = blk_layout.lineAt(i)
                    doc_y = top + line.y()
                    screen_y = doc_y - scroll_y
                    last_screen_y = screen_y
                    if -line_h <= screen_y <= widget_h:
                        text = str(visual_no + 1)
                        tw = fm.horizontalAdvance(text)
                        painter.drawText(self.width() - tw - 2, int(screen_y + ascent), text)
                        visible_count += 1
                    visual_no += 1
            block = block.next()

        if self.reference_edit is not None:
            ref_count = 0
            rb = self.reference_edit.document().begin()
            while rb.isValid():
                rl = rb.layout()
                if rl is not None:
                    rn = rl.lineCount()
                    ref_count += rn if rn > 0 else 1
                rb = rb.next()
            if visual_no < ref_count:
                next_y = (last_screen_y + line_h) if last_screen_y is not None else 0
                for i in range(visual_no, ref_count):
                    if -line_h <= next_y <= widget_h:
                        text = str(i + 1)
                        tw = fm.horizontalAdvance(text)
                        painter.drawText(self.width() - tw - 2, int(next_y + ascent), text)
                        visible_count += 1
                    next_y += line_h
                visual_no = ref_count

        if __debug__:
            print(f"[行号] 总视觉行={visual_no} 可见绘制={visible_count}")

        if not getattr(self, '_in_resize', False) and visual_no > 0:
            digits = len(str(visual_no))
            char_w = fm.horizontalAdvance('0')
            need_w = char_w * digits + 4
            if need_w != self.width():
                self._in_resize = True
                self.setFixedWidth(need_w)
                self._in_resize = False

    def update_line_numbers(self):
        self.update()

    def refresh_theme(self):
        self.setStyleSheet(f"background-color:{theme.get('line_number_bg')}; border:none;")
        self.update()


class SegmentedToggle(QWidget):
    """二态分段切换控件：抄写|默写，带滑块滑动动画"""
    toggled = pyqtSignal(int)

    def __init__(self, labels=None, parent=None):
        super().__init__(parent)
        self._index = 0
        self._slide = 0.0
        self._labels = labels if labels else ["抄写", "默写"]
        self.setFixedHeight(25)
        self.setFixedWidth(104)
        self._anim = QPropertyAnimation(self, b"slideProgress")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setMouseTracking(True)

    def getSlideProgress(self):
        return self._slide

    def setSlideProgress(self, v):
        self._slide = v
        self.update()

    slideProgress = pyqtProperty(float, getSlideProgress, setSlideProgress)

    def currentIndex(self):
        return self._index

    def setCurrentIndex(self, idx):
        if idx == self._index:
            return
        self._index = idx
        self._anim.stop()
        self._anim.setStartValue(self._slide)
        self._anim.setEndValue(float(idx))
        self._anim.start()
        self.toggled.emit(idx)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            new_idx = 0 if event.position().x() < self.width() / 2 else 1
            if new_idx != self._index:
                self.setCurrentIndex(new_idx)

    def mouseMoveEvent(self, event):
        idx = 0 if event.position().x() < self.width() / 2 else 1
        if idx != self._index:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.unsetCursor()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        half = w / 2.0
        margin = 3
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(*theme.rgb('toggle_bg')))
        painter.drawRoundedRect(0, 0, w, h, 4, 4)
        painter.setPen(QPen(QColor(*theme.rgb('toggle_border')), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 4, 4)
        slider_w = half - margin * 2
        slider_h = h - margin * 2
        slider_x = margin + self._slide * half
        slider_y = margin
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(*theme.rgb('toggle_slider')))
        painter.drawRoundedRect(QRectF(slider_x, slider_y, slider_w, slider_h), 4, 4)
        font = QFont(painter.font())
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        for i, lab in enumerate(self._labels):
            if abs(self._slide - i) < 0.5:
                painter.setPen(QColor(255, 255, 255))
            else:
                painter.setPen(QColor(*theme.rgb('toggle_text_off')))
            painter.drawText(QRectF(i * half, 0, half, h), Qt.AlignmentFlag.AlignCenter, lab)


class HighlightableTextEdit(QTextEdit):
    """支持按视觉行号高亮的文本框：自绘半透明矩形，空行也能高亮"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._highlight_lines = set()
        self._dictation_active = False
        self._countdown_value = None
        self._manual_pending = False
        self._manual_btn_hover = False
        self._manual_btn_rect = None

    def set_highlight_lines(self, lines):
        self._highlight_lines = set(int(x) for x in lines)
        self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._countdown_value is not None and self._countdown_value > 0:
            painter = QPainter(self.viewport())
            painter.setPen(QColor(*theme.rgb('countdown_red')))
            font = QFont(self.font())
            font.setBold(True)
            painter.setFont(font)
            fm = painter.fontMetrics()
            rect = self.cursorRect()
            painter.drawText(rect.left(), rect.top() + fm.ascent(), str(self._countdown_value))
            return
        if self._manual_pending:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            font = QFont(self.font())
            font.setBold(True)
            painter.setFont(font)
            fm = painter.fontMetrics()
            cur_rect = self.cursorRect()
            text = "记住了"
            text_w = fm.horizontalAdvance(text)
            text_h = fm.height()
            btn_x = cur_rect.left()
            btn_y = cur_rect.top()
            btn_w = text_w + 12
            btn_h = text_h + 4
            btn_rect = QRectF(btn_x, btn_y, btn_w, btn_h)
            self._manual_btn_rect = btn_rect
            if self._manual_btn_hover:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(*theme.rgb('manual_green')))
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(*theme.rgb('manual_green_dark')))
            painter.drawRoundedRect(btn_rect, 4, 4)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, text)
            return
        if not self._highlight_lines:
            return
        painter = QPainter(self.viewport())
        painter.setFont(self.font())
        fm = painter.fontMetrics()
        ascent = fm.ascent()
        yellow = QColor(*theme.rgb('highlight_yellow'))
        black = QColor(0, 0, 0)
        doc = self.document()
        doc_layout = doc.documentLayout()
        scroll_y = self.verticalScrollBar().value()
        vp_w = self.viewport().width()
        fm_h = fm.height()
        block = doc.begin()
        visual_no = 0
        while block.isValid():
            bl = block.layout()
            if bl is not None:
                n = bl.lineCount()
                if n == 0:
                    n = 1
                top0 = doc_layout.blockBoundingRect(block).y()
                pos_x = bl.position().x()
                block_text = block.text()
                for i in range(n):
                    if (visual_no + 1) in self._highlight_lines:
                        line = bl.lineAt(i)
                        y = top0 + line.y() - scroll_y
                        h = line.rect().height()
                        if h <= 0:
                            h = fm_h
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.setBrush(yellow)
                        painter.drawRoundedRect(QRectF(2, int(y), vp_w - 4, int(h)), 4, 4)
                        if not self._dictation_active:
                            tl = line.textLength()
                            if tl > 0:
                                ts = line.textStart()
                                text = block_text[ts:ts+tl]
                                x = pos_x + line.x()
                                painter.setPen(black)
                                painter.drawText(QPoint(int(x), int(y + ascent)), text)
                    visual_no += 1
            block = block.next()


class RoundItemDelegate(QStyledItemDelegate):
    """圆角选中背景的列表项 delegate"""
    def paint(self, painter, option, index):
        rect = option.rect
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(*theme.rgb('bg_select')))
            painter.drawRoundedRect(rect.adjusted(1, 0, -1, 0), 4, 4)
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        painter.setFont(option.font)
        if option.state & QStyle.StateFlag.State_MouseOver and not (option.state & QStyle.StateFlag.State_Selected):
            painter.setPen(QColor(*theme.rgb('text_hover')))
        else:
            painter.setPen(QColor(*theme.rgb('text_label')))
        painter.drawText(rect.adjusted(8, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, text)
        painter.restore()

    def sizeHint(self, option, index):
        return super().sizeHint(option, index)


class ProgressDelegate(QStyledItemDelegate):
    """章节列表项 delegate：按复写进度绘制背景进度条"""
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window_ref = window

    def _progress(self, index):
        w = self.window_ref
        chapter_title = index.data(Qt.ItemDataRole.DisplayRole)
        novels = w.novel_list.selectedItems()
        if not novels:
            return 0.0
        novel_name = novels[0].text()
        if novel_name not in w.novel_data:
            return 0.0
        chapters = w.novel_data[novel_name].get('chapters', {})
        if chapter_title not in chapters:
            return 0.0
        total = len(chapters[chapter_title].replace('\n', ''))
        if total == 0:
            return 0.0
        key = f"{novel_name}||{chapter_title}"
        written = len(w.chapter_write_memory.get(key, "").replace('\n', ''))
        return written / total

    def paint(self, painter, option, index):
        rect = option.rect
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setBrush(QColor(*theme.rgb('bg_select')))
            painter.drawRoundedRect(rect.adjusted(1, 0, -1, 0), 4, 4)
        ratio = self._progress(index)
        if ratio > 0:
            c = QColor(*theme.rgb('progress_green'))
            c.setAlpha(140)
            painter.setBrush(c)
            br = QRect(rect.left(), rect.top(), int(rect.width() * ratio), rect.height())
            r = min(4, br.width() // 2, br.height() // 2)
            painter.drawRoundedRect(br, r, r)
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        painter.setFont(option.font)
        if option.state & QStyle.StateFlag.State_MouseOver and not (option.state & QStyle.StateFlag.State_Selected):
            painter.setPen(QColor(*theme.rgb('text_hover')))
        else:
            painter.setPen(QColor(*theme.rgb('text_label')))
        painter.drawText(rect.adjusted(8, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, text)
        painter.restore()

    def sizeHint(self, option, index):
        return super().sizeHint(option, index)


class CustomTitleBar(QFrame):
    """自定义无边框标题栏，支持拖动、双击最大化"""
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.setFixedHeight(36)
        self.setStyleSheet(self._build_style())
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        self.title_label = QLabel("抄写默写训练工具")
        self.title_label.setObjectName("win_title")
        layout.addWidget(self.title_label)
        layout.addStretch(1)

        btn_settings = QPushButton("⚙")
        btn_settings.setObjectName("settings_btn")
        btn_settings.setToolTip("设置")
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(btn_settings, 0, Qt.AlignmentFlag.AlignVCenter)
        self.btn_settings = btn_settings

        sep_settings = QFrame()
        sep_settings.setFixedWidth(1)
        sep_settings.setFixedHeight(14)
        sep_settings.setStyleSheet("background-color:#3c4663; border:none;")
        layout.addWidget(sep_settings, 0, Qt.AlignmentFlag.AlignVCenter)

        btn_min = QPushButton("−")
        btn_min.setObjectName("title_btn")
        btn_min.clicked.connect(self.parent_window.showMinimized)
        layout.addWidget(btn_min)

        btn_max = QPushButton("□")
        btn_max.setObjectName("title_btn")
        btn_max.setStyleSheet("padding-bottom:5px;")
        btn_max.clicked.connect(self.toggle_max)
        layout.addWidget(btn_max)
        self.btn_max = btn_max

        btn_close = QPushButton("×")
        btn_close.setObjectName("close_btn")
        btn_close.clicked.connect(self.parent_window.close)
        layout.addWidget(btn_close)

        self._drag_pos = None

        self.btn_settings.clicked.connect(self._open_settings)

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def _build_style(self):
        return f"""
        QFrame{{
            background-color:{theme.get('bg_title_bar')};
            border:none;
        }}
        QLabel#win_title{{
            color:{theme.get('text_title')};
            font-size:13pt;
            font-weight:bold;
            padding-left:12px;
        }}
        QPushButton#title_btn{{
            background-color:transparent;
            color:{theme.get('text_label')};
            border:none;
            width:36px;
            height:36px;
            font-size:14pt;
        }}
        QPushButton#title_btn:hover{{
            background-color:{theme.get('bg_title_btn_hover')};
        }}
        QPushButton#font_btn{{
            background-color:{theme.get('bg_btn')};
            color:{theme.get('text_sub')};
            border:1px solid {theme.get('border')};
            border-radius:4px;
            padding:0 8px;
            font-size:16pt;
        }}
        QPushButton#font_btn:hover{{
            background-color:{theme.get('bg_btn_hover')};
        }}
        QPushButton#close_btn{{
            background-color:transparent;
            color:{theme.get('text_label')};
            border:none;
            width:36px;
            height:36px;
            font-size:14pt;
        }}
        QPushButton#close_btn:hover{{
            background-color:{theme.get('close_hover')};
        }}
        QPushButton#settings_btn{{
            background-color:transparent;
            color:{theme.get('text_label')};
            border:none;
            width:30px;
            height:30px;
            font-size:12pt;
            padding-bottom:2px;
        }}
        QPushButton#settings_btn:hover{{
            background-color:{theme.get('bg_title_btn_hover')};
        }}
        """

    def refresh_theme(self):
        self.setStyleSheet(self._build_style())

    def toggle_max(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self.btn_max.setText("□")
        else:
            self.parent_window.showMaximized()
            self.btn_max.setText("❐")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            self._drag_local = event.position().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None:
            gp = event.globalPosition().toPoint()
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
                new_x = int(gp.x() - self._drag_local.x())
                new_y = int(gp.y() - self._drag_local.y())
                self.parent_window.move(new_x, new_y)
                self._drag_pos = gp
                return
            delta = gp - self._drag_pos
            self.parent_window.move(self.parent_window.pos() + delta)
            self._drag_pos = gp

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        self.toggle_max()


class SettingsDialog(QDialog):
    """全局设置面板"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setFixedSize(360, 160)
        self._window = getattr(parent, 'parent_window', None)
        self._apply_style()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        title = QLabel("主题")
        title.setObjectName("settings_title")
        row.addWidget(title)
        row.addStretch(1)

        self.swatch_dark = self._make_swatch(theme.DARK['bg_main'], 'dark')
        self.swatch_light = self._make_swatch(theme.LIGHT['bg_main'], 'light')
        self._update_swatch_border()
        row.addWidget(self.swatch_dark)
        row.addWidget(self.swatch_light)
        layout.addLayout(row)
        layout.addStretch(1)

    def _apply_style(self):
        self.setStyleSheet(f"""
        QDialog{{ background-color:{theme.get('bg_panel')}; }}
        QLabel#settings_title{{ color:{theme.get('text')}; font-size:13pt; font-weight:bold; }}
        """)

    def _make_swatch(self, color, name):
        sw = QPushButton()
        sw.setFixedSize(28, 28)
        sw.setCursor(Qt.CursorShape.PointingHandCursor)
        sw._theme_name = name
        sw._bg = color
        sw.clicked.connect(lambda: self._select(name))
        return sw

    def _select(self, name):
        if self._window is not None:
            self._window.apply_theme(name)
        self._apply_style()
        self._update_swatch_border()

    def _update_swatch_border(self):
        cur = theme.current_name()
        for sw in (self.swatch_dark, self.swatch_light):
            if sw._theme_name == cur:
                sw.setStyleSheet(f"background-color:{sw._bg}; border:2px solid {theme.get('accent_gold')}; border-radius:4px;")
            else:
                sw.setStyleSheet(f"background-color:{sw._bg}; border:1px solid {theme.get('border')}; border-radius:4px;")


class QtWidgetInspector(QObject):
    """调试用控件检查器：Ctrl + 左键点击打印控件信息，发布打包不生效"""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.app = QApplication.instance()
        self.app.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                modifiers = event.modifiers()
                if modifiers & Qt.KeyboardModifier.ControlModifier:
                    self._inspect(obj, event)
                    return True
        return False

    def _inspect(self, obj, event):
        global_pos = event.globalPosition().toPoint()
        widget = self.app.widgetAt(global_pos)
        if widget is None:
            return

        print("=" * 70)
        print(f"[控件检查] 点击位置: {global_pos.x()}, {global_pos.y()}")
        print("-" * 70)
        print(f"objectName : {widget.objectName() or '(空)'}")
        print(f"类名       : {widget.__class__.__name__}")
        g = widget.geometry()
        print(f"geometry   : x={g.x()} y={g.y()} w={g.width()} h={g.height()}")
        print("-" * 70)
        ss = widget.styleSheet()
        print(f"styleSheet : {ss if ss.strip() else '(空)'}")
        print("-" * 70)

        chain = []
        cur = widget
        while cur is not None:
            name = cur.objectName() or cur.__class__.__name__
            chain.append(name)
            cur = cur.parent()
        chain.reverse()
        print("层级链     : " + " -> ".join(chain))
        print("=" * 70)
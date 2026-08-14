import sys
import sqlite3
import os
import csv
import re
import subprocess
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog, 
                             QListWidget, QStackedWidget, QDialog, QFormLayout, QTextEdit, 
                             QScrollArea, QFrame, QAbstractItemView, QGroupBox, QGraphicsDropShadowEffect,
                             QDateTimeEdit, QCheckBox)
from PyQt6.QtCore import Qt, QUrl, QTimer, QDateTime
from PyQt6.QtGui import QFont, QColor, QDesktopServices

DB_FILE = os.path.expanduser("~/Documents/job_tracker.db")


STATUS_OPTIONS = [
    "待投递", "已投递", "筛选中", "测评待完成", "测评已完成", 
    "笔试待考", "笔试完成", "一面", "二面", "终面", "offer", "挂了"
]
ASSESSMENT_STATUS_OPTIONS = ["未收到测评", "待完成测评", "已完成测评", "测评过期"]

# ================= 全局 QSS 样式表 =================
GLOBAL_QSS = """
QMainWindow, QDialog {
    background-color: #F7F8FA;
}
QWidget {
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
    color: #1E293B;
}

QFrame.CardFrame {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
}

QGroupBox {
    font-weight: bold;
    font-size: 13px;
    color: #1E293B;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 14px;
    background-color: #FFFFFF;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #FFFFFF;
    color: #1E293B;
}

QLineEdit, QTextEdit, QComboBox, QDateTimeEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 22px;
    color: #1E293B;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus {
    border: 1px solid #2563EB;
}
QComboBox::drop-down, QDateTimeEdit::drop-down {
    border: none;
    width: 24px;
}

QPushButton {
    background-color: #64748B;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #475569;
}
QPushButton:pressed {
    background-color: #334155;
}

QTableWidget {
    background-color: #FFFFFF;
    alternate-background-color: #F1F5F9;
    gridline-color: #CBD5E1;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    selection-background-color: #E2E8F0;
    selection-color: #1E293B;
}
QHeaderView::section {
    background-color: #E2E8F0;
    color: #1E293B;
    padding: 8px 6px;
    font-weight: bold;
    border: none;
    border-bottom: 1px solid #CBD5E1;
}

QFrame#SidebarCard {
    background-color: #E9EDF2;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
}
QListWidget#SidebarList {
    background-color: transparent;
    border: none;
    outline: none;
    padding: 4px;
}
QListWidget#SidebarList::item {
    height: 40px;
    border-radius: 6px;
    margin-bottom: 4px;
    padding-left: 10px;
    color: #64748B;
    font-weight: 500;
}
QListWidget#SidebarList::item:hover {
    background-color: #FFFFFF;
    color: #1E293B;
}
QListWidget#SidebarList::item:selected {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: bold;
}

QScrollBar:vertical {
    border: none;
    background: #F7F8FA;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #64748B;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

def apply_card_shadow(widget):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(10)
    shadow.setColor(QColor(0, 0, 0, 12))
    shadow.setOffset(0, 2)
    widget.setGraphicsEffect(shadow)

# ================= 强力时间解析与倒计时生成 =================
def parse_any_datetime(s):
    if not s:
        return None
    clean_s = str(s).strip()
    if not clean_s:
        return None
        
    # 提取所有纯数字
    digits = re.sub(r'\D', '', clean_s)
    
    try:
        if len(digits) == 8:    # YYYYMMDD -> 当天 23:59:59
            return datetime(int(digits[:4]), int(digits[4:6]), int(digits[6:8]), 23, 59, 59)
        elif len(digits) == 10: # YYYYMMDDHH
            return datetime(int(digits[:4]), int(digits[4:6]), int(digits[6:8]), int(digits[8:10]), 0, 0)
        elif len(digits) == 12: # YYYYMMDDHHMM (如 202608151500)
            return datetime(int(digits[:4]), int(digits[4:6]), int(digits[6:8]), int(digits[8:10]), int(digits[10:12]), 0)
        elif len(digits) == 14: # YYYYMMDDHHMMSS
            return datetime(int(digits[:4]), int(digits[4:6]), int(digits[6:8]), int(digits[8:10]), int(digits[10:12]), int(digits[12:14]))
    except ValueError:
        pass

    # 尝试带分隔符的格式
    formats = [
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(clean_s, fmt)
            if fmt in ["%Y-%m-%d", "%Y/%m/%d"]:
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt
        except ValueError:
            pass
            
    return None

def format_countdown(deadline_str):
    target_dt = parse_any_datetime(deadline_str)
    if not target_dt:
        return "-", "#1E293B"
        
    now = datetime.now()
    diff = target_dt - now
    total_seconds = int(diff.total_seconds())
    
    if total_seconds <= 0:
        return "⚠️ 已截止", "#DC4444"
        
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    # 构建纯倒计时文本
    if days > 0:
        cd_text = f"{days}天 {hours:02d}小时 {minutes:02d}分"
    else:
        cd_text = f"{hours:02d}小时 {minutes:02d}分 "
        
    if total_seconds < 12 * 3600:
        color = "#DC4444"  # 12小时内 紧急红
    elif total_seconds < 24 * 3600:
        color = "#F59E0B"  # 24小时内 警告橙
    else:
        color = "#2563EB"  # 时间充裕 蓝
        
    return cd_text, color

# ================= 数据库操作 =================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS delivery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT, position TEXT, channel TEXT, jd_link TEXT,
        deliver_time TEXT, resume_version TEXT, referrer TEXT, location TEXT,
        salary TEXT, deadline TEXT, status TEXT, remark TEXT,
        create_time TEXT, update_time TEXT
    )''')
    
    for col, def_val in [("assessment_email", "''"), ("assessment_link", "''"), 
                         ("assessment_deadline", "''"), ("assessment_status", "'未收到测评'")]:
        try: cursor.execute(f"ALTER TABLE delivery ADD COLUMN {col} TEXT DEFAULT {def_val}")
        except: pass

    cursor.execute('''CREATE TABLE IF NOT EXISTS resume_file (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resume_code TEXT DEFAULT '',
        resume_name TEXT, file_path TEXT, comment TEXT, create_time TEXT
    )''')
    
    try: cursor.execute("ALTER TABLE resume_file ADD COLUMN resume_code TEXT DEFAULT ''")
    except: pass
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS interview_note (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        delivery_id INTEGER, note_content TEXT, note_time TEXT,
        FOREIGN KEY(delivery_id) REFERENCES delivery(id)
    )''')
    conn.commit()
    
    cursor.execute("SELECT id, resume_code FROM resume_file WHERE resume_code = '' OR resume_code IS NULL")
    rows = cursor.fetchall()
    for row in rows:
        cursor.execute("UPDATE resume_file SET resume_code=? WHERE id=?", (f"R{row[0]:02d}", row[0]))
    conn.commit()
    conn.close()

def db_query(query, args=()):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, args)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def db_execute(query, args=()):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(query, args)
    conn.commit()
    conn.close()

def current_time(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def open_local_file(path):
    if not os.path.exists(path): return False
    try:
        if sys.platform == "win32": os.startfile(path)
        elif sys.platform == "darwin": subprocess.call(["open", path])
        else: subprocess.call(["xdg-open", path])
        return True
    except Exception: return False

def open_web_url(url_str):
    if not url_str: return
    if not url_str.startswith("http"): url_str = "http://" + url_str
    QDesktopServices.openUrl(QUrl(url_str))

# ================= 弹窗模块 =================
class UrgentAssessmentDialog(QDialog):
    def __init__(self, records, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⏰ 紧急测评提醒")
        self.resize(720, 320)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        warn_card = QFrame()
        warn_card.setProperty("class", "CardFrame")
        warn_card.setStyleSheet("background-color: #FFFBEB; border: 1px solid #FDE68A;")
        apply_card_shadow(warn_card)
        warn_layout = QHBoxLayout(warn_card)
        warn_layout.setContentsMargins(14, 10, 14, 10)

        warn_lbl = QLabel(f"⚠️ 发现 {len(records)} 个线上测评即将在 12 小时内过期，请尽快完成！")
        warn_lbl.setStyleSheet("color: #DC4444; font-weight: bold; font-size: 13px; border: none; background: transparent;")
        warn_layout.addWidget(warn_lbl)
        layout.addWidget(warn_card)

        table_card = QFrame()
        table_card.setProperty("class", "CardFrame")
        apply_card_shadow(table_card)
        tc_layout = QVBoxLayout(table_card)
        tc_layout.setContentsMargins(8, 8, 8, 8)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["公司", "岗位", "测评倒计时", "操作"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setRowCount(len(records))
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(38)

        for i, r in enumerate(records):
            table.setItem(i, 0, QTableWidgetItem(r['company']))
            table.setItem(i, 1, QTableWidgetItem(r['position']))
            
            display_text, color_hex = format_countdown(r['assessment_deadline'])
            time_item = QTableWidgetItem(display_text)
            time_item.setForeground(QColor(color_hex))
            time_item.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
            table.setItem(i, 2, time_item)
            
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)
            
            open_btn = QPushButton("🌐 打开")
            open_btn.setStyleSheet("background-color: #2563EB; color: #FFFFFF; border: none;")
            copy_btn = QPushButton("复制链接")
            
            if r['assessment_link']:
                open_btn.clicked.connect(lambda checked, l=r['assessment_link']: open_web_url(l))
                copy_btn.clicked.connect(lambda checked, l=r['assessment_link']: QApplication.clipboard().setText(l))
            else:
                open_btn.setDisabled(True)
                copy_btn.setDisabled(True)
            
            btn_layout.addWidget(open_btn)
            btn_layout.addWidget(copy_btn)
            table.setCellWidget(i, 3, btn_widget)

        tc_layout.addWidget(table)
        layout.addWidget(table_card)

        close_btn = QPushButton("我知道了")
        close_btn.setFixedWidth(120)
        close_btn.setStyleSheet("background-color: #2563EB; color: #FFFFFF; font-weight: bold; border: none;")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

class DeliveryDialog(QDialog):
    def __init__(self, parent=None, delivery_id=None):
        super().__init__(parent)
        self.delivery_id = delivery_id
        self.setWindowTitle("投递记录编辑" if delivery_id else "新增投递记录")
        self.setMinimumWidth(520)
        self.setup_ui()
        if self.delivery_id:
            self.load_data()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)
        
        basic_group = QGroupBox("基础网申信息")
        apply_card_shadow(basic_group)
        basic_layout = QFormLayout()
        basic_layout.setContentsMargins(16, 16, 16, 16)
        basic_layout.setVerticalSpacing(10)
        basic_layout.setHorizontalSpacing(12)
        basic_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.company_input = QLineEdit()
        self.position_input = QLineEdit()
        self.status_cb = QComboBox()
        self.status_cb.addItems(STATUS_OPTIONS)
        
        self.resume_cb = QComboBox()
        self.resume_cb.addItem("未绑定(无)", "")
        resumes = db_query("SELECT resume_code, resume_name FROM resume_file ORDER BY id ASC")
        for res in resumes: 
            self.resume_cb.addItem(f"{res['resume_code']} ({res['resume_name']})", res['resume_code'])

        self.deadline_input = QLineEdit()
        self.deadline_input.setPlaceholderText("YYYY-MM-DD")
        self.jd_input = QLineEdit()
        self.remark_input = QTextEdit()
        self.remark_input.setMaximumHeight(65)

        basic_layout.addRow("公司名称*:", self.company_input)
        basic_layout.addRow("岗位名称*:", self.position_input)
        basic_layout.addRow("网申状态:", self.status_cb)
        basic_layout.addRow("绑定简历:", self.resume_cb)
        basic_layout.addRow("网申截止:", self.deadline_input)
        basic_layout.addRow("JD 链接:", self.jd_input)
        basic_layout.addRow("详细备注:", self.remark_input)
        basic_group.setLayout(basic_layout)
        main_layout.addWidget(basic_group)
        
        ass_group = QGroupBox("【线上测评信息】")
        apply_card_shadow(ass_group)
        ass_layout = QFormLayout()
        ass_layout.setContentsMargins(16, 16, 16, 16)
        ass_layout.setVerticalSpacing(10)
        ass_layout.setHorizontalSpacing(12)
        ass_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.ass_email_input = QLineEdit()
        self.ass_link_input = QLineEdit()
        
        # 可视化日历与具体时分选择
        ass_deadline_box = QWidget()
        ass_dl_layout = QHBoxLayout(ass_deadline_box)
        ass_dl_layout.setContentsMargins(0, 0, 0, 0)
        ass_dl_layout.setSpacing(8)

        self.ass_deadline_cb = QCheckBox("启用截止时间")
        self.ass_deadline_dt = QDateTimeEdit(QDateTime.currentDateTime().addDays(1))
        self.ass_deadline_dt.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.ass_deadline_dt.setCalendarPopup(True)
        self.ass_deadline_dt.setEnabled(False)
        
        self.ass_deadline_cb.toggled.connect(self.ass_deadline_dt.setEnabled)

        ass_dl_layout.addWidget(self.ass_deadline_cb)
        ass_dl_layout.addWidget(self.ass_deadline_dt, 1)

        self.ass_status_cb = QComboBox()
        self.ass_status_cb.addItems(ASSESSMENT_STATUS_OPTIONS)
        
        ass_layout.addRow("邮箱:", self.ass_email_input)
        ass_layout.addRow("链接:", self.ass_link_input)
        ass_layout.addRow("截止时间:", ass_deadline_box)
        ass_layout.addRow("测评状态:", self.ass_status_cb)
        ass_group.setLayout(ass_layout)
        main_layout.addWidget(ass_group)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(90)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("💾 保存记录")
        save_btn.setFixedWidth(110)
        save_btn.setStyleSheet("background-color: #2563EB; color: #FFFFFF; font-weight: bold; border: none;")
        save_btn.clicked.connect(self.save_data)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

    def load_data(self):
        record = db_query("SELECT * FROM delivery WHERE id=?", (self.delivery_id,))[0]
        self.company_input.setText(record['company'])
        self.position_input.setText(record['position'])
        self.status_cb.setCurrentText(record['status'])
        
        target_code = record.get('resume_version', '')
        idx = self.resume_cb.findData(target_code)
        if idx >= 0:
            self.resume_cb.setCurrentIndex(idx)
            
        self.deadline_input.setText(record['deadline'])
        self.jd_input.setText(record['jd_link'])
        self.remark_input.setPlainText(record['remark'])
        
        self.ass_email_input.setText(record.get('assessment_email', ''))
        self.ass_link_input.setText(record.get('assessment_link', ''))
        
        raw_ass_dl = record.get('assessment_deadline', '')
        dt = parse_any_datetime(raw_ass_dl)
        if dt:
            qdt = QDateTime(dt.year, dt.month, dt.day, dt.hour, dt.minute)
            self.ass_deadline_dt.setDateTime(qdt)
            self.ass_deadline_cb.setChecked(True)
        else:
            self.ass_deadline_cb.setChecked(False)

        self.ass_status_cb.setCurrentText(record.get('assessment_status', '未收到测评'))

    def save_data(self):
        c = self.company_input.text().strip()
        p = self.position_input.text().strip()
        if not c or not p:
            QMessageBox.warning(self, "错误", "公司和岗位名称不能为空！")
            return
            
        resume_code_val = self.resume_cb.currentData()
        
        if self.ass_deadline_cb.isChecked():
            ass_dl = self.ass_deadline_dt.dateTime().toString("yyyy-MM-dd HH:mm")
        else:
            ass_dl = ""

        ass_status = self.ass_status_cb.currentText()
        if ass_dl and ass_status == "未收到测评":
            ass_status = "待完成测评"

        if not self.delivery_id:
            db_execute('''INSERT INTO delivery (
                            company, position, status, resume_version, deadline, jd_link, remark, 
                            assessment_email, assessment_link, assessment_deadline, assessment_status, create_time
                          ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                       (c, p, self.status_cb.currentText(), resume_code_val, self.deadline_input.text(), self.jd_input.text(), self.remark_input.toPlainText(),
                        self.ass_email_input.text(), self.ass_link_input.text(), ass_dl, ass_status, current_time()))
        else:
            db_execute('''UPDATE delivery SET 
                            company=?, position=?, status=?, resume_version=?, deadline=?, jd_link=?, remark=?, 
                            assessment_email=?, assessment_link=?, assessment_deadline=?, assessment_status=?, update_time=?
                          WHERE id=?''',
                       (c, p, self.status_cb.currentText(), resume_code_val, self.deadline_input.text(), self.jd_input.text(), self.remark_input.toPlainText(),
                        self.ass_email_input.text(), self.ass_link_input.text(), ass_dl, ass_status, current_time(), self.delivery_id))
        self.accept()

# ================= 主窗口 =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LuckyQInG的小助手")
        self.resize(1180, 760)
        
        QApplication.instance().setStyleSheet(GLOBAL_QSS)
        
        init_db()
        self.setup_ui()
        self.load_deliveries()
        self.load_resumes()
        self.check_assessments()

        # 每秒刷新倒计时
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdowns)
        self.timer.start(1000)

    def check_assessments(self):
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M")
        db_execute("UPDATE delivery SET assessment_status='测评过期' WHERE assessment_status='待完成测评' AND assessment_deadline < ? AND assessment_deadline != ''", (now_str,))
        
        # 核心改动：由原来的 48 小时改为 12 小时提醒
        twelve_hours_later = (now + timedelta(hours=12)).strftime("%Y-%m-%d %H:%M")
        urgent_records = db_query("SELECT * FROM delivery WHERE assessment_status='待完成测评' AND assessment_deadline >= ? AND assessment_deadline <= ?", (now_str, twelve_hours_later))
        if urgent_records:
            self.ass_dialog = UrgentAssessmentDialog(urgent_records, self)
            self.ass_dialog.exec()

    def update_countdowns(self):
        if self.sidebar.currentRow() != 0:
            return  # 仅在“投递记录”页面刷新倒计时
            
        for row in range(self.del_table.rowCount()):
            raw_deadline = self.del_table.item(row, 4).data(Qt.ItemDataRole.UserRole)
            if raw_deadline:
                display_text, color_hex = format_countdown(raw_deadline)
                item = self.del_table.item(row, 4)
                if item:
                    item.setText(display_text)
                    item.setForeground(QColor(color_hex))

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(14)

        sidebar_card = QFrame()
        sidebar_card.setObjectName("SidebarCard")
        sidebar_card.setFixedWidth(180)
        apply_card_shadow(sidebar_card)
        sidebar_layout = QVBoxLayout(sidebar_card)
        sidebar_layout.setContentsMargins(8, 12, 8, 12)
        sidebar_layout.setSpacing(8)

        logo_lbl = QLabel("🎯 TrustMe")
        logo_lbl.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        logo_lbl.setStyleSheet("color: #1E293B; padding-left: 6px; margin-bottom: 6px;")
        sidebar_layout.addWidget(logo_lbl)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("SidebarList")
        self.sidebar.addItems(["💼  投递记录", "📄  简历管理", "📝  面试笔记", "📊  数据看板", "💾  数据备份"])
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self.switch_page)
        sidebar_layout.addWidget(self.sidebar)

        main_layout.addWidget(sidebar_card)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        self.stack.addWidget(self.create_delivery_page())
        self.stack.addWidget(self.create_resume_page())
        self.stack.addWidget(self.create_note_page())
        self.stack.addWidget(self.create_dashboard_page())
        self.stack.addWidget(self.create_backup_page())

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        if index == 0: self.load_deliveries()
        elif index == 1: self.load_resumes()
        elif index == 2: self.refresh_note_combobox()
        elif index == 3: self.refresh_dashboard()

    # ================= 页面1: 投递记录 =================
    def create_delivery_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        toolbar_card = QFrame()
        toolbar_card.setProperty("class", "CardFrame")
        apply_card_shadow(toolbar_card)
        toolbar = QHBoxLayout(toolbar_card)
        toolbar.setContentsMargins(14, 10, 14, 10)
        toolbar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索公司/岗位...")
        self.search_input.setFixedWidth(200)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部状态"] + STATUS_OPTIONS)

        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.load_deliveries)

        add_btn = QPushButton("➕ 新增投递")
        add_btn.setStyleSheet("background-color: #2563EB; color: #FFFFFF; font-weight: bold; border: none;")
        add_btn.clicked.connect(self.open_add_delivery)

        toolbar.addWidget(self.search_input)
        toolbar.addWidget(QLabel("状态:"))
        toolbar.addWidget(self.status_filter)
        toolbar.addWidget(search_btn)
        toolbar.addStretch()
        toolbar.addWidget(add_btn)
        layout.addWidget(toolbar_card)

        table_card = QFrame()
        table_card.setProperty("class", "CardFrame")
        apply_card_shadow(table_card)
        tc_layout = QVBoxLayout(table_card)
        tc_layout.setContentsMargins(10, 10, 10, 10)

        self.del_table = QTableWidget()
        self.del_table.setColumnCount(8)
        self.del_table.setHorizontalHeaderLabels(["公司", "岗位", "状态", "测评状态", "截止倒计时", "简历", "操作", "看简历"])
        
        header = self.del_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        self.del_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.del_table.setAlternatingRowColors(True)
        self.del_table.verticalHeader().setVisible(False)
        self.del_table.verticalHeader().setDefaultSectionSize(48)

        tc_layout.addWidget(self.del_table)
        layout.addWidget(table_card)
        return page

    def load_deliveries(self):
        kw = f"%{self.search_input.text()}%"
        stat = self.status_filter.currentText()
        query = "SELECT * FROM delivery WHERE (company LIKE ? OR position LIKE ?)"
        args = [kw, kw]
        if stat != "全部状态":
            query += " AND status = ?"
            args.append(stat)
        query += " ORDER BY id DESC"
        
        records = db_query(query, tuple(args))
        self.del_table.setRowCount(len(records))
        for row, r in enumerate(records):
            self.del_table.setItem(row, 0, QTableWidgetItem(r['company']))
            self.del_table.setItem(row, 1, QTableWidgetItem(r['position']))
            self.del_table.setItem(row, 2, QTableWidgetItem(r['status']))
            
            ass_status_item = QTableWidgetItem(r.get('assessment_status', '未收到测评'))
            if r.get('assessment_status') == '待完成测评':
                ass_status_item.setForeground(QColor("#F59E0B"))
                ass_status_item.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
            elif r.get('assessment_status') == '测评过期':
                ass_status_item.setForeground(QColor("#DC4444"))
            self.del_table.setItem(row, 3, ass_status_item)
            
            # 纯倒计时单元格渲染
            raw_deadline = r.get('assessment_deadline', '')
            display_text, color_hex = format_countdown(raw_deadline)
            time_item = QTableWidgetItem(display_text)
            time_item.setData(Qt.ItemDataRole.UserRole, raw_deadline)
            time_item.setForeground(QColor(color_hex))
            time_item.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.del_table.setItem(row, 4, time_item)
            
            resume_code = r.get('resume_version') or "-"
            code_item = QTableWidgetItem(resume_code)
            code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            code_item.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
            self.del_table.setItem(row, 5, code_item)
            
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)
            
            edit_btn = QPushButton("E")
            edit_btn.setFixedWidth(46)
            edit_btn.clicked.connect(lambda checked, rid=r['id']: self.open_edit_delivery(rid))
            
            del_btn = QPushButton("D")
            del_btn.setFixedWidth(46)
            del_btn.setStyleSheet("background-color: #DC4444; color: #FFFFFF; border: none;")
            del_btn.clicked.connect(lambda checked, rid=r['id']: self.delete_delivery(rid))
            
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(del_btn)
            self.del_table.setCellWidget(row, 6, btn_widget)
            
            if resume_code != "-":
                view_res_btn = QPushButton("查看")
                view_res_btn.setStyleSheet("background-color: transparent; color: #2563EB; font-weight: bold; border: none;")
                view_res_btn.clicked.connect(lambda checked, code=resume_code: self.view_bound_resume_by_code(code))
                self.del_table.setCellWidget(row, 7, view_res_btn)

    def view_bound_resume_by_code(self, code):
        res = db_query("SELECT file_path, resume_name FROM resume_file WHERE resume_code=? OR resume_name=?", (code, code))
        if res and res[0]['file_path']:
            if not open_local_file(res[0]['file_path']):
                QMessageBox.warning(self, "错误", f"无法打开文件：\n{res[0]['file_path']}\n可能已被移动或删除。")
        else:
            QMessageBox.warning(self, "错误", f"未找到编码为 [{code}] 的简历文件。")

    def open_add_delivery(self):
        if DeliveryDialog(self).exec(): self.load_deliveries()
    def open_edit_delivery(self, rid):
        if DeliveryDialog(self, delivery_id=rid).exec(): self.load_deliveries()
    def delete_delivery(self, rid):
        reply = QMessageBox.question(self, "确认", "确定删除这条投递记录吗？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            db_execute("DELETE FROM delivery WHERE id=?", (rid,))
            self.load_deliveries()

    # ================= 页面2: 简历管理 =================
    def create_resume_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        form_card = QFrame()
        form_card.setProperty("class", "CardFrame")
        apply_card_shadow(form_card)
        form_layout = QHBoxLayout(form_card)
        form_layout.setContentsMargins(14, 14, 14, 14)
        form_layout.setSpacing(10)
        
        self.res_code_input = QLineEdit()
        self.res_code_input.setPlaceholderText("编码(如:R01)")
        self.res_code_input.setFixedWidth(110)
        
        self.res_name_input = QLineEdit()
        self.res_name_input.setPlaceholderText("版本描述名称(如:产品经理精修版_v1)")
        
        self.res_path_input = QLineEdit()
        self.res_path_input.setReadOnly(True)
        self.res_path_input.setPlaceholderText("请选择 PDF 文件路径...")
        
        pick_btn = QPushButton("选择PDF")
        pick_btn.clicked.connect(self.pick_resume_file)
        
        save_btn = QPushButton("💾 保存简历")
        save_btn.setStyleSheet("background-color: #2563EB; color: #FFFFFF; font-weight: bold; border: none;")
        save_btn.clicked.connect(self.save_resume)
        
        form_layout.addWidget(QLabel("编码:"))
        form_layout.addWidget(self.res_code_input)
        form_layout.addWidget(QLabel("名称:"))
        form_layout.addWidget(self.res_name_input)
        form_layout.addWidget(self.res_path_input)
        form_layout.addWidget(pick_btn)
        form_layout.addWidget(save_btn)
        layout.addWidget(form_card)
        
        table_card = QFrame()
        table_card.setProperty("class", "CardFrame")
        apply_card_shadow(table_card)
        tc_layout = QVBoxLayout(table_card)
        tc_layout.setContentsMargins(10, 10, 10, 10)

        self.res_table = QTableWidget()
        self.res_table.setColumnCount(4)
        self.res_table.setHorizontalHeaderLabels(["简历编码", "版本描述名称", "文件路径", "操作"])
        self.res_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.res_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.res_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.res_table.setAlternatingRowColors(True)
        self.res_table.verticalHeader().setVisible(False)
        self.res_table.verticalHeader().setDefaultSectionSize(40)

        tc_layout.addWidget(self.res_table)
        layout.addWidget(table_card)
        return page

    def pick_resume_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "选择简历", "", "PDF Files (*.pdf)")
        if fname: self.res_path_input.setText(fname)

    def save_resume(self):
        code = self.res_code_input.text().strip().upper()
        n = self.res_name_input.text().strip()
        p = self.res_path_input.text().strip()
        
        if not n or not p:
            QMessageBox.warning(self, "错误", "简历名称和文件路径不能为空！")
            return
            
        if not code:
            existing = db_query("SELECT id FROM resume_file")
            code = f"R{(len(existing) + 1):02d}"

        exist_code = db_query("SELECT id FROM resume_file WHERE resume_code=?", (code,))
        if exist_code:
            QMessageBox.warning(self, "错误", f"简历编码 [{code}] 已存在，请换一个编码！")
            return

        db_execute("INSERT INTO resume_file (resume_code, resume_name, file_path, create_time) VALUES (?,?,?,?)", 
                   (code, n, p, current_time()))
        
        self.res_code_input.clear()
        self.res_name_input.clear()
        self.res_path_input.clear()
        self.load_resumes()

    def load_resumes(self):
        records = db_query("SELECT * FROM resume_file ORDER BY id DESC")
        self.res_table.setRowCount(len(records))
        for row, r in enumerate(records):
            code_item = QTableWidgetItem(r['resume_code'])
            code_item.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
            code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.res_table.setItem(row, 0, code_item)
            self.res_table.setItem(row, 1, QTableWidgetItem(r['resume_name']))
            self.res_table.setItem(row, 2, QTableWidgetItem(r['file_path']))
            
            btn_w = QWidget()
            bl = QHBoxLayout(btn_w)
            bl.setContentsMargins(4, 2, 4, 2)
            bl.setSpacing(6)

            open_btn = QPushButton("打开PDF")
            open_btn.clicked.connect(lambda checked, p=r['file_path']: open_local_file(p))

            del_btn = QPushButton("删除")
            del_btn.setStyleSheet("background-color: #DC4444; color: #FFFFFF; border: none;")
            del_btn.clicked.connect(lambda checked, rid=r['id']: (db_execute("DELETE FROM resume_file WHERE id=?",(rid,)), self.load_resumes()))

            bl.addWidget(open_btn)
            bl.addWidget(del_btn)
            self.res_table.setCellWidget(row, 3, btn_w)

    # ================= 页面3: 面试笔记 =================
    def create_note_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        input_card = QFrame()
        input_card.setProperty("class", "CardFrame")
        apply_card_shadow(input_card)
        ic_layout = QVBoxLayout(input_card)
        ic_layout.setContentsMargins(14, 14, 14, 14)
        ic_layout.setSpacing(10)

        cb_layout = QHBoxLayout()
        cb_layout.addWidget(QLabel("关联投递记录:"))
        self.note_delivery_cb = QComboBox()
        self.note_delivery_cb.currentIndexChanged.connect(self.load_notes)
        cb_layout.addWidget(self.note_delivery_cb, 1)
        ic_layout.addLayout(cb_layout)

        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("记录面试高频问题、项目复盘、改进点...")
        self.note_input.setMaximumHeight(85)
        ic_layout.addWidget(self.note_input)

        save_btn = QPushButton("💾 保存面试笔记")
        save_btn.setFixedWidth(130)
        save_btn.setStyleSheet("background-color: #2563EB; color: #FFFFFF; font-weight: bold; border: none;")
        save_btn.clicked.connect(self.save_note)
        ic_layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addWidget(input_card)

        list_card = QFrame()
        list_card.setProperty("class", "CardFrame")
        apply_card_shadow(list_card)
        lc_layout = QVBoxLayout(list_card)
        lc_layout.setContentsMargins(10, 10, 10, 10)

        self.note_scroll_area = QScrollArea()
        self.note_scroll_area.setWidgetResizable(True)
        self.note_scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.note_container = QWidget()
        self.note_layout = QVBoxLayout(self.note_container)
        self.note_layout.setContentsMargins(0, 0, 0, 0)
        self.note_layout.setSpacing(10)

        self.note_scroll_area.setWidget(self.note_container)
        lc_layout.addWidget(self.note_scroll_area)

        layout.addWidget(list_card)
        return page

    def refresh_note_combobox(self):
        self.note_delivery_cb.clear()
        for d in db_query("SELECT id, company, position FROM delivery ORDER BY id DESC"):
            self.note_delivery_cb.addItem(f"{d['company']} - {d['position']}", d['id'])

    def load_notes(self):
        for i in reversed(range(self.note_layout.count())):
            w = self.note_layout.itemAt(i).widget()
            if w: w.deleteLater()
            
        d_id = self.note_delivery_cb.currentData()
        if not d_id: return
        
        notes = db_query("SELECT * FROM interview_note WHERE delivery_id=? ORDER BY id DESC", (d_id,))
        if not notes:
            empty_lbl = QLabel("暂无相关的面试笔记记录。")
            empty_lbl.setStyleSheet("color: #64748B; padding: 12px;")
            self.note_layout.addWidget(empty_lbl)
            return

        for n in notes:
            frame = QFrame()
            frame.setProperty("class", "CardFrame")
            frame.setStyleSheet("QFrame { background-color: #F8FAFC; border: 1px solid #CBD5E1; }")
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(12, 10, 12, 10)
            fl.setSpacing(6)

            time_lbl = QLabel(f"⏱️ 记录时间: {n['note_time']}")
            time_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
            content_lbl = QLabel(n['note_content'])
            content_lbl.setWordWrap(True)
            content_lbl.setStyleSheet("font-size: 13px; color: #1E293B;")

            del_btn = QPushButton("删除")
            del_btn.setFixedWidth(55)
            del_btn.setStyleSheet("background-color: #DC4444; color: #FFFFFF; font-size: 11px; border: none;")
            del_btn.clicked.connect(lambda checked, nid=n['id']: (db_execute("DELETE FROM interview_note WHERE id=?",(nid,)), self.load_notes()))

            fl.addWidget(time_lbl)
            fl.addWidget(content_lbl)
            fl.addWidget(del_btn, alignment=Qt.AlignmentFlag.AlignRight)
            self.note_layout.addWidget(frame)

    def save_note(self):
        d_id = self.note_delivery_cb.currentData()
        content = self.note_input.toPlainText().strip()
        if d_id and content:
            db_execute("INSERT INTO interview_note (delivery_id, note_content, note_time) VALUES (?,?,?)", (d_id, content, current_time()))
            self.note_input.clear()
            self.load_notes()

    # ================= 页面4: 数据看板 =================
    def create_dashboard_page(self):
        page = QWidget()
        self.dashboard_layout = QVBoxLayout(page)
        self.dashboard_layout.setContentsMargins(0, 0, 0, 0)
        self.dashboard_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        return page

    def refresh_dashboard(self):
        for i in reversed(range(self.dashboard_layout.count())):
            widget = self.dashboard_layout.itemAt(i).widget()
            if widget: widget.deleteLater()

        dash_card = QFrame()
        dash_card.setProperty("class", "CardFrame")
        dash_card.setMinimumWidth(750)
        apply_card_shadow(dash_card)
        dc_layout = QVBoxLayout(dash_card)
        dc_layout.setContentsMargins(24, 20, 24, 20)
        dc_layout.setSpacing(16)

        title = QLabel("📊 全生命周期漏斗模型")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #1E293B;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dc_layout.addWidget(title)
        dc_layout.addSpacing(10)

        records = db_query("SELECT status, assessment_status FROM delivery")
        total = len(records)
        
        written_statuses = ['测评待完成', '测评已完成', '笔试待考', '笔试完成', '一面', '二面', '终面', 'offer']
        interview_statuses = ['一面', '二面', '终面', 'offer']
        pool_statuses = ['终面', 'offer']
        offer_statuses = ['offer']

        stage_written = sum(1 for r in records if r['status'] in written_statuses or r['assessment_status'] in ['待完成测评', '已完成测评', '测评过期'])
        stage_interview = sum(1 for r in records if r['status'] in interview_statuses)
        stage_pool = sum(1 for r in records if r['status'] in pool_statuses)
        stage_offer = sum(1 for r in records if r['status'] in offer_statuses)

        stages = [
            ("总投递量", total, "#1E293B"),
            ("通过初筛 (笔试/测评)", stage_written, "#64748B"),
            ("进入面试 (一面/二面)", stage_interview, "#2563EB"),
            ("进入终面", stage_pool, "#7C3AED"),
            ("斩获 Offer", stage_offer, "#F59E0B")
        ]

        if total == 0:
            dc_layout.addWidget(QLabel("暂无投递数据，快去投递你的第一份简历吧！"), alignment=Qt.AlignmentFlag.AlignCenter)
            self.dashboard_layout.addWidget(dash_card)
            return

        for name, count, color in stages:
            ratio = (count / total) if total > 0 else 0
            bar_width = max(int(620 * ratio), 280)
            
            frame = QFrame()
            frame.setFixedSize(bar_width, 38)
            frame.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
            flayout = QVBoxLayout(frame)
            flayout.setContentsMargins(0, 0, 0, 0)
            
            percent_str = f" {(count/total*100):.1f}%" if total > 0 else ""
            lbl = QLabel(f"{name} : {count} {percent_str}")
            lbl.setStyleSheet("color: white; font-weight: bold;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            flayout.addWidget(lbl)
            
            dc_layout.addWidget(frame, alignment=Qt.AlignmentFlag.AlignHCenter)

        dc_layout.addSpacing(16)
        summary = QGroupBox("诊断与策略建议")
        slayout = QVBoxLayout(summary)
        slayout.setContentsMargins(14, 14, 14, 14)
        
        resume_rate = (stage_written/total*100) if total > 0 else 0
        interview_rate = (stage_offer/stage_interview*100) if stage_interview > 0 else 0
        
        diag_text = f"• 简历初筛通过率: {resume_rate:.1f}%\n"
        if resume_rate < 20: diag_text += "  [建议] 你的初筛通过率偏低，建议去【简历管理】上传一份精修版本，多找人帮忙修改，优化JD关键词匹配度。\n\n"
        else: diag_text += "  [优秀] 简历写得很棒，初筛通过率健康！\n\n"
        
        diag_text += f"• 面试至Offer转化率: {interview_rate:.1f}%\n"
        if stage_interview > 0 and interview_rate < 15: diag_text += "  [建议] 虽然拿到了面试，但最终转化偏低。建议多在【面试笔记】中进行复盘，练习八股文与项目陈述。"
        elif stage_interview > 0: diag_text += "  [优秀] 面试发挥稳定，转化率不错，继续保持！"
        
        diag_lbl = QLabel(diag_text)
        diag_lbl.setStyleSheet("color: #1E293B; line-height: 1.5;")
        slayout.addWidget(diag_lbl)
        dc_layout.addWidget(summary)

        self.dashboard_layout.addWidget(dash_card)

    # ================= 页面5: 数据备份 =================
    def create_backup_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setProperty("class", "CardFrame")
        apply_card_shadow(card)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(30, 30, 30, 30)
        c_layout.setSpacing(16)

        info_lbl = QLabel("📁 数据备份与导出")
        info_lbl.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        info_lbl.setStyleSheet("color: #1E293B;")
        
        desc_lbl = QLabel("所有投递与测评数据均安全保留在本地 SQLite 数据库中。\n导出 CSV 会自动包含关联的简历编码，方便用 Excel 进行分析。")
        desc_lbl.setStyleSheet("color: #64748B; line-height: 1.6;")

        export_btn = QPushButton("📥 导出全部投递记录为 CSV")
        export_btn.setFixedSize(240, 44)
        export_btn.setStyleSheet("background-color: #2563EB; color: #FFFFFF; font-weight: bold; border: none;")
        export_btn.clicked.connect(self.export_csv)

        c_layout.addWidget(info_lbl)
        c_layout.addWidget(desc_lbl)
        c_layout.addWidget(export_btn)
        c_layout.addStretch()

        layout.addWidget(card)
        return page

    def export_csv(self):
        records = db_query("SELECT * FROM delivery")
        if not records: return QMessageBox.warning(self, "提示", "数据库为空。")
        fname, _ = QFileDialog.getSaveFileName(self, "保存CSV", f"delivery_export_{datetime.now().strftime('%Y%m%d')}.csv", "CSV Files (*.csv)")
        if fname:
            with open(fname, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)
            QMessageBox.information(self, "成功", f"数据已成功导出至：\n{fname}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

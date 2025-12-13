import sys, asyncio, threading, os
import nextcord
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QTextEdit, 
    QVBoxLayout, QLineEdit, QLabel, QComboBox, QHBoxLayout,
    QGroupBox, QStatusBar, QListWidget, QStackedWidget, QFrame,
    QSlider, QSpinBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPalette, QColor, QFont, QKeySequence
from PyQt5.QtWidgets import QShortcut
from dotenv import load_dotenv
import google.generativeai as genai
import re

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TOKEN:
    print("HATA: .env dosyasında DISCORD_TOKEN bulunamadı!")
    print("Lütfen .env dosyasını oluşturun ve içine DISCORD_TOKEN=bot_tokeniniz yazın")
    sys.exit(1)

# Yapay zeka için yasaklı kalıplar
FORBIDDEN_PATTERNS = [
    r"child\s*porn", r"c\.p", r"childabuse", r"zoophilia", r"bestiality",
]

intents = nextcord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

client = nextcord.Client(intents=intents)

# Yapay zeka durumu
ai_enabled = False
ai_mode = "normal"  # normal, sarcastic, crazy
ai_temperature = 0.7

class LogSignals(QObject):
    log_message = pyqtSignal(str, str)  
    update_gui = pyqtSignal()
    update_guilds = pyqtSignal()

log_signals = LogSignals()

# Farklı log türleri için ayrı listeler
all_logs = []
server_logs = []
dm_logs = []
error_logs = []
ai_logs = []

class BotPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("balikesirlicalintipanel.py")
        self.resize(1000, 600)
        
        # Sinyal-slot bağlantılarını kur
        log_signals.log_message.connect(self.add_log_message)
        log_signals.update_gui.connect(self.update_logs)
        log_signals.update_guilds.connect(self.update_guilds_list)
        
        self.init_ui()
        
    def init_ui(self):
        # Ana layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sol navbar
        navbar = QFrame()
        navbar.setFixedWidth(200)
        navbar.setStyleSheet("""
            QFrame {
                background-color: #2f3136;
                border: none;
            }
            QListWidget {
                background-color: #2f3136;
                color: #8e9297;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 10px;
                border: none;
            }
            QListWidget::item:selected {
                background-color: #42464d;
                color: white;
                border-left: 3px solid #7289da;
            }
            QListWidget::item:hover {
                background-color: #36393f;
            }
        """)
        
        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        
        # Navbar başlığı
        title_label = QLabel("Discord Bot Panel")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 16px;
                padding: 15px;
                background-color: #23272a;
                border-bottom: 1px solid #1e2124;
            }
        """)
        title_label.setFixedHeight(50)
        
        # Navbar menü
        self.nav_list = QListWidget()
        self.nav_list.addItems(["Ana Menü", "Sunucu Mesajları", "DM Mesajları", "Hata Logları", "Yapay Zeka"])
        self.nav_list.setCurrentRow(0)
        
        # Bot kontrol butonları
        control_frame = QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: #23272a;
                border-top: 1px solid #1e2124;
            }
        """)
        control_layout = QVBoxLayout()
        control_layout.setContentsMargins(10, 10, 10, 10)
        
        self.start_btn = QPushButton("Botu Başlat")
        self.stop_btn = QPushButton("Botu Durdur")
        self.stop_btn.setEnabled(False)
        
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #43b581;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3ca374;
            }
            QPushButton:disabled {
                background-color: #4f545c;
            }
        """)
        
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f04747;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d83c3c;
            }
            QPushButton:disabled {
                background-color: #4f545c;
            }
        """)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_frame.setLayout(control_layout)
        
        nav_layout.addWidget(title_label)
        nav_layout.addWidget(self.nav_list)
        nav_layout.addWidget(control_frame)
        navbar.setLayout(nav_layout)
        
        # Sağ içerik alanı
        self.content_stack = QStackedWidget()
        
        # Ana sayfa
        self.main_page = self.create_main_page()
        self.content_stack.addWidget(self.main_page)
        
        # Sunucu mesajları sayfası
        self.server_page = self.create_server_page()
        self.content_stack.addWidget(self.server_page)
        
        # DM mesajları sayfası
        self.dm_page = self.create_dm_page()
        self.content_stack.addWidget(self.dm_page)
        
        # Hata logları sayfası
        self.error_page = self.create_error_page()
        self.content_stack.addWidget(self.error_page)
        
        # Yapay Zeka sayfası
        self.ai_page = self.create_ai_page()
        self.content_stack.addWidget(self.ai_page)
        
        # Navbar seçimini dinle
        self.nav_list.currentRowChanged.connect(self.on_page_changed)
        
        main_layout.addWidget(navbar)
        main_layout.addWidget(self.content_stack)
        
        self.setLayout(main_layout)
        
        # Event bağlantıları
        self.start_btn.clicked.connect(self.start_bot)
        self.stop_btn.clicked.connect(self.stop_bot)
        
        # Kısayol tuşlarını ekle
        self.setup_shortcuts()
        
    def setup_shortcuts(self):
        # F1 tuşu - Ana Menü
        shortcut_f1 = QShortcut(QKeySequence("F1"), self)
        shortcut_f1.activated.connect(lambda: self.nav_list.setCurrentRow(0))
        
        # F2 tuşu - Sunucu Mesajları
        shortcut_f2 = QShortcut(QKeySequence("F2"), self)
        shortcut_f2.activated.connect(lambda: self.nav_list.setCurrentRow(1))
        
        # F3 tuşu - DM Mesajları
        shortcut_f3 = QShortcut(QKeySequence("F3"), self)
        shortcut_f3.activated.connect(lambda: self.nav_list.setCurrentRow(2))
        
        # F4 tuşu - Hata Logları
        shortcut_f4 = QShortcut(QKeySequence("F4"), self)
        shortcut_f4.activated.connect(lambda: self.nav_list.setCurrentRow(3))
        
        # F7 tuşu - Yapay Zeka
        shortcut_f7 = QShortcut(QKeySequence("F7"), self)
        shortcut_f7.activated.connect(lambda: self.nav_list.setCurrentRow(4))

        # F5 tuşu - Botu Başlat
        shortcut_f5 = QShortcut(QKeySequence("F5"), self)
        shortcut_f5.activated.connect(self.start_bot)

        # F6 tuşu - Botu Durdur
        shortcut_f6 = QShortcut(QKeySequence("F6"), self)
        shortcut_f6.activated.connect(self.stop_bot)
        
    def create_ai_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        
        # Yapay Zeka Durumu
        status_group = QGroupBox("Yapay Zeka Durumu")
        status_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #1e2124;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #7289da;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        status_layout = QHBoxLayout()
        
        self.ai_status_label = QLabel("Kapalı")
        self.ai_status_label.setStyleSheet("""
            QLabel {
                color: #f04747;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        
        self.ai_toggle_btn = QPushButton("Yapay Zekayı Aç")
        self.ai_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #43b581;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3ca374;
            }
        """)
        
        status_layout.addWidget(QLabel("Durum:"))
        status_layout.addWidget(self.ai_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.ai_toggle_btn)
        status_group.setLayout(status_layout)
        
        # Yapay Zeka Ayarları
        settings_group = QGroupBox("Yapay Zeka Ayarları")
        settings_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #1e2124;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #7289da;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        settings_layout = QVBoxLayout()
        
        # Mod seçimi
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mod:"))
        self.ai_mode_combo = QComboBox()
        self.ai_mode_combo.addItems(["Normal", "Alaycı", "Delirme"])
        self.ai_mode_combo.setCurrentText("Normal")
        self.ai_mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #36393f;
                color: #dcddde;
                border: 1px solid #1e2124;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        mode_layout.addWidget(self.ai_mode_combo)
        mode_layout.addStretch()
        
        # Sıcaklık ayarı
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Hayal Gücü (0-1):"))
        self.ai_temp_spin = QDoubleSpinBox()
        self.ai_temp_spin.setRange(0.0, 1.0)
        self.ai_temp_spin.setSingleStep(0.1)
        self.ai_temp_spin.setValue(0.7)
        self.ai_temp_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #36393f;
                color: #dcddde;
                border: 1px solid #1e2124;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        temp_layout.addWidget(self.ai_temp_spin)
        temp_layout.addStretch()
        
        settings_layout.addLayout(mode_layout)
        settings_layout.addLayout(temp_layout)
        settings_group.setLayout(settings_layout)
        
        # Yapay Zeka Logları
        log_group = QGroupBox("Yapay Zeka Logları")
        log_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #1e2124;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #7289da;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        log_layout = QVBoxLayout()
        self.log_area_ai = QTextEdit()
        self.log_area_ai.setReadOnly(True)
        self.log_area_ai.setStyleSheet("""
            QTextEdit {
                background-color: #36393f;
                color: #dcddde;
                border: 1px solid #1e2124;
                border-radius: 3px;
            }
        """)
        log_layout.addWidget(self.log_area_ai)
        log_group.setLayout(log_layout)
        
        layout.addWidget(status_group)
        layout.addWidget(settings_group)
        layout.addWidget(log_group)
        page.setLayout(layout)
        
        # Event bağlantıları
        self.ai_toggle_btn.clicked.connect(self.toggle_ai)
        self.ai_mode_combo.currentTextChanged.connect(self.update_ai_mode)
        self.ai_temp_spin.valueChanged.connect(self.update_ai_temperature)
        
        return page
        
    def toggle_ai(self):
        global ai_enabled
        
        if not GEMINI_API_KEY:
            log_signals.log_message.emit("ERROR", "GEMINI_API_KEY bulunamadı. Lütfen .env dosyasını kontrol edin.")
            return
            
        ai_enabled = not ai_enabled
        
        if ai_enabled:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                self.ai_status_label.setText("Açık")
                self.ai_status_label.setStyleSheet("""
                    QLabel {
                        color: #43b581;
                        font-weight: bold;
                        font-size: 14px;
                    }
                """)
                self.ai_toggle_btn.setText("Yapay Zekayı Kapat")
                log_signals.log_message.emit("AI", "Yapay zeka aktif edildi.")
            except Exception as e:
                log_signals.log_message.emit("ERROR", f"Yapay zeka başlatılamadı: {str(e)}")
                ai_enabled = False
        else:
            self.ai_status_label.setText("Kapalı")
            self.ai_status_label.setStyleSheet("""
                QLabel {
                    color: #f04747;
                    font-weight: bold;
                    font-size: 14px;
                }
            """)
            self.ai_toggle_btn.setText("Yapay Zekayı Aç")
            log_signals.log_message.emit("AI", "Yapay zeka devre dışı bırakıldı.")
    
    def update_ai_mode(self, mode_text):
        global ai_mode
        mode_mapping = {
            "Normal": "normal",
            "Alaycı": "sarcastic",
            "Delirme": "crazy"
        }
        ai_mode = mode_mapping.get(mode_text, "normal")
        log_signals.log_message.emit("AI", f"Yapay zeka modu değiştirildi: {mode_text}")
    
    def update_ai_temperature(self, value):
        global ai_temperature
        ai_temperature = value
        log_signals.log_message.emit("AI", f"Yapay zeka sıcaklık değeri değiştirildi: {value}")
        
    # Yeni metod
    def on_page_changed(self, index):
        self.content_stack.setCurrentIndex(index)
        self.refresh_logs(index)

    def refresh_logs(self, page_index):
        if page_index == 0:  # Ana Menü
            pass
        elif page_index == 1:  # Sunucu Mesajları
            self.log_area_server.clear()
            for log in server_logs:
                self.log_area_server.append(log)
        elif page_index == 2:  # DM Mesajları
            self.log_area_dm.clear()
            for log in dm_logs:
                self.log_area_dm.append(log)
        elif page_index == 3:  # Hata Logları
            self.log_area_error.clear()
            for log in error_logs:
                self.log_area_error.append(log)
        elif page_index == 4:  # Yapay Zeka
            self.log_area_ai.clear()
            for log in ai_logs:
                self.log_area_ai.append(log)
        
    def create_main_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        
        # Tüm loglar
        log_group = QGroupBox("Tüm Mesaj Logları")
        log_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #1e2124;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #7289da;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        log_layout = QVBoxLayout()
        self.log_area_all = QTextEdit()
        self.log_area_all.setReadOnly(True)
        self.log_area_all.setStyleSheet("""
            QTextEdit {
                background-color: #36393f;
                color: #dcddde;
                border: 1px solid #1e2124;
                border-radius: 3px;
            }
        """)
        log_layout.addWidget(self.log_area_all)
        log_group.setLayout(log_layout)
        
        layout.addWidget(log_group)
        page.setLayout(layout)
        return page
        
    def create_server_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        
        # Sunucu mesaj logları
        log_group = QGroupBox("Sunucu Mesaj Logları")
        log_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #1e2124;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #7289da;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        log_layout = QVBoxLayout()
        self.log_area_server = QTextEdit()
        self.log_area_server.setReadOnly(True)
        self.log_area_server.setStyleSheet("""
            QTextEdit {
                background-color: #36393f;
                color: #dcddde;
                border: 1px solid #1e2124;
                border-radius: 3px;
            }
        """)
        log_layout.addWidget(self.log_area_server)
        log_group.setLayout(log_layout)
        
        # Sunucuya mesaj gönderme
        send_group = QGroupBox("Sunucuya Mesaj Gönder")
        send_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #1e2124;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #7289da;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        send_layout = QVBoxLayout()
        
        guild_layout = QHBoxLayout()
        guild_layout.addWidget(QLabel("Sunucu:"))
        self.guild_box = QComboBox()
        self.guild_box.addItem("Sunucu seçilmedi")
        self.guild_box.setStyleSheet("""
            QComboBox {
                background-color: #36393f;
                color: #dcddde;
                border: 1px solid #1e2124;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        guild_layout.addWidget(self.guild_box)
        
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("Kanal:"))
        self.channel_box = QComboBox()
        self.channel_box.addItem("Kanal seçilmedi")
        self.channel_box.setStyleSheet("""
            QComboBox {
                background-color: #36393f;
                color: #dcddde;
                border: 1px solid #1e2124;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        channel_layout.addWidget(self.channel_box)
        
        self.guild_msg_input = QLineEdit()
        self.guild_msg_input.setPlaceholderText("Sunucuya gönderilecek mesaj...")
        self.guild_msg_input.setStyleSheet("""
            QLineEdit {
                background-color: #36393f;
                color: #dcddde;
                border: 1px solid #1e2124;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        
        self.send_guild_btn = QPushButton("Sunucuya Mesaj Gönder")
        self.send_guild_btn.setStyleSheet("""
            QPushButton {
                background-color: #7289da;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #677bc4;
            }
        """)
        
        send_layout.addLayout(guild_layout)
        send_layout.addLayout(channel_layout)
        send_layout.addWidget(QLabel("Mesaj:"))
        send_layout.addWidget(self.guild_msg_input)
        send_layout.addWidget(self.send_guild_btn)
        send_group.setLayout(send_layout)
        
        layout.addWidget(log_group)
        layout.addWidget(send_group)
        page.setLayout(layout)
        
        # Event bağlantıları
        self.send_guild_btn.clicked.connect(self.send_guild_msg)
        self.guild_box.currentIndexChanged.connect(self.update_channels)
        
        return page
        
    def create_dm_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        
        # DM mesaj logları
        log_group = QGroupBox("DM Mesaj Logları")
        log_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #1e2124;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #7289da;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        log_layout = QVBoxLayout()
        self.log_area_dm = QTextEdit()
        self.log_area_dm.setReadOnly(True)
        self.log_area_dm.setStyleSheet("""
            QTextEdit {
                background-color: #36393f;
                color: #dcddde;
                border: 1px solid #1e2124;
                border-radius: 3px;
            }
        """)
        log_layout.addWidget(self.log_area_dm)
        log_group.setLayout(log_layout)
        
        # DM gönderme
        send_group = QGroupBox("DM Gönder")
        send_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #1e2124;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #7289da;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        send_layout = QVBoxLayout()
        
        # Sunucu seçimi
        server_layout = QHBoxLayout()
        server_layout.addWidget(QLabel("Sunucu:"))
        self.dm_guild_box = QComboBox()
        self.dm_guild_box.addItem("Sunucu seçilmedi")
        self.dm_guild_box.setStyleSheet("""
            QComboBox {
                background-color: #36393f;
                color: #dcddde;
                border: 1px solid #1e2124;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        server_layout.addWidget(self.dm_guild_box)
        
        # Üye seçimi
        member_layout = QHBoxLayout()
        member_layout.addWidget(QLabel("Üye:"))
        self.member_box = QComboBox()
        self.member_box.addItem("Üye seçilmedi")
        self.member_box.setStyleSheet("""
            QComboBox {
                background-color: #36393f;
                color: #dcddde;
                border: 1px solid #1e2124;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        member_layout.addWidget(self.member_box)
        
        self.dm_user_input = QLineEdit()
        self.dm_user_input.setPlaceholderText("Kullanıcı ID gir...")
        self.dm_user_input.setStyleSheet("""
            QLineEdit {
                background-color: #36393f;
                color: #dcddde;
                border: 1px solid #1e2124;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        
        self.dm_msg_input = QLineEdit()
        self.dm_msg_input.setPlaceholderText("Gönderilecek mesaj...")
        self.dm_msg_input.setStyleSheet("""
            QLineEdit {
                background-color: #36393f;
                color: #dcddde;
                border: 1px solid #1e2124;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        
        self.send_dm_btn = QPushButton("DM Gönder")
        self.send_dm_btn.setStyleSheet("""
            QPushButton {
                background-color: #7289da;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #677bc4;
            }
        """)
        
        send_layout.addLayout(server_layout)
        send_layout.addLayout(member_layout)
        send_layout.addWidget(QLabel("Kullanıcı ID:"))
        send_layout.addWidget(self.dm_user_input)
        send_layout.addWidget(QLabel("Mesaj:"))
        send_layout.addWidget(self.dm_msg_input)
        send_layout.addWidget(self.send_dm_btn)
        send_group.setLayout(send_layout)
        
        layout.addWidget(log_group)
        layout.addWidget(send_group)
        page.setLayout(layout)
        
        # Event bağlantıları
        self.send_dm_btn.clicked.connect(self.send_dm)
        self.dm_guild_box.currentIndexChanged.connect(self.update_dm_members)
        self.member_box.currentIndexChanged.connect(self.on_member_selected)
        
        return page
            
    def update_dm_members(self):
        self.member_box.clear()
        self.member_box.addItem("Üye seçilmedi")
        
        guild_name = self.dm_guild_box.currentText()
        if guild_name != "Sunucu seçilmedi":
            guild = next((g for g in client.guilds if g.name == guild_name), None)
            if guild:
                for member in guild.members:
                    if not member.bot:  # Botları listeleme
                        self.member_box.addItem(f"{member.name}#{member.discriminator}", member.id)

    def on_member_selected(self, index):
        if index > 0:  # "Üye seçilmedi" değilse
            user_id = self.member_box.currentData()
            self.dm_user_input.setText(str(user_id))

    def create_error_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        
        # Hata logları
        log_group = QGroupBox("Hata Logları")
        log_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #1e2124;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #7289da;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        log_layout = QVBoxLayout()
        self.log_area_error = QTextEdit()
        self.log_area_error.setReadOnly(True)
        self.log_area_error.setStyleSheet("""
            QTextEdit {
                background-color: #36393f;
                color: #dcddde;
                border: 1px solid #1e2124;
                border-radius: 3px;
            }
        """)
        log_layout.addWidget(self.log_area_error)
        log_group.setLayout(log_layout)
        
        layout.addWidget(log_group)
        page.setLayout(layout)
        return page
        
    @pyqtSlot(str, str)
    def add_log_message(self, log_type, message):
        # Logları ilgili listelere ekle
        all_logs.append(message)
        
        if log_type == "SERVER":
            server_logs.append(message)
            # Sunucu mesajları sayfası aktifse mesajı göster
            if self.content_stack.currentIndex() == 1:  # Sunucu Mesajları sayfası
                self.log_area_server.append(message)
            # Ayrıca ana menüde de göster
            self.log_area_all.append(message)
        elif log_type == "DM":
            dm_logs.append(message)
            # DM sayfası aktifse mesajı göster
            if self.content_stack.currentIndex() == 2:  # DM Mesajları sayfası
                self.log_area_dm.append(message)
            # Ayrıca ana menüde de göster
            self.log_area_all.append(message)
        elif log_type == "ERROR":
            error_logs.append(message)
            # Hata sayfası aktifse mesajı göster
            if self.content_stack.currentIndex() == 3:  # Hata Logları sayfası
                self.log_area_error.append(message)
            # Ayrıca ana menüde de göster
            self.log_area_all.append(message)
        elif log_type == "INFO":
            # Bilgi mesajlarını sadece ana menüde göster
            self.log_area_all.append(message)
        elif log_type == "AI":
            ai_logs.append(message)
            # Yapay zeka sayfası aktifse mesajı göster
            if self.content_stack.currentIndex() == 4:  # Yapay Zeka sayfası
                self.log_area_ai.append(message)
            # Ayrıca ana menüde de göster
            self.log_area_all.append(message)
            
    def update_logs(self):
        # Sadece scroll position'ı güncelle
        self.log_area_all.verticalScrollBar().setValue(
            self.log_area_all.verticalScrollBar().maximum()
        )
        self.log_area_server.verticalScrollBar().setValue(
            self.log_area_server.verticalScrollBar().maximum()
        )
        self.log_area_dm.verticalScrollBar().setValue(
            self.log_area_dm.verticalScrollBar().maximum()
        )
        self.log_area_error.verticalScrollBar().setValue(
            self.log_area_error.verticalScrollBar().maximum()
        )
        self.log_area_ai.verticalScrollBar().setValue(
            self.log_area_ai.verticalScrollBar().maximum()
        )
        
    @pyqtSlot()
    def update_guilds_list(self):
        # Sunucu mesajları sayfasındaki sunucu kutusunu güncelle
        self.guild_box.clear()
        self.guild_box.addItem("Sunucu seçilmedi")
        
        # DM sayfasındaki sunucu kutusunu da güncelle
        self.dm_guild_box.clear()
        self.dm_guild_box.addItem("Sunucu seçilmedi")
        
        for guild in client.guilds:
            self.guild_box.addItem(guild.name)
            self.dm_guild_box.addItem(guild.name)
        
    def send_dm(self):
        user_id = self.dm_user_input.text().strip()
        msg = self.dm_msg_input.text().strip()
        if user_id and msg:
            asyncio.run_coroutine_threadsafe(
                send_dm(int(user_id), msg), client.loop
            )
            log_signals.log_message.emit("DM", f"[DM] {user_id}: {msg}")
            self.dm_msg_input.clear()
        
    def send_guild_msg(self):
        guild_name = self.guild_box.currentText()
        channel_name = self.channel_box.currentText()
        msg = self.guild_msg_input.text().strip()
        if guild_name != "Sunucu seçilmedi" and channel_name != "Kanal seçilmedi" and msg:
            guild = next((g for g in client.guilds if g.name == guild_name), None)
            if guild:
                channel = next((c for c in guild.text_channels if c.name == channel_name), None)
                if channel:
                    asyncio.run_coroutine_threadsafe(
                        channel.send(msg), client.loop
                    )
                    log_signals.log_message.emit("SERVER", f"[{guild.name}#{channel.name}] -> {msg}")
                    self.guild_msg_input.clear()
        
    def start_bot(self):
        try:
            # Botu thread'de başlat
            self.bot_thread = threading.Thread(target=run_bot, daemon=True)
            self.bot_thread.start()
            
            log_signals.log_message.emit("INFO", "Bot başlatılıyor...")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
        except Exception as e:
            error_msg = f"Bot başlatılırken hata: {str(e)}"
            log_signals.log_message.emit("ERROR", error_msg)

    def stop_bot(self):
        asyncio.run_coroutine_threadsafe(client.close(), client.loop)
        log_signals.log_message.emit("INFO", "Bot durduruldu.")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
    def update_channels(self):
        guild_name = self.guild_box.currentText()
        if guild_name != "Sunucu seçilmedi":
            guild = next((g for g in client.guilds if g.name == guild_name), None)
            if guild:
                self.channel_box.clear()
                self.channel_box.addItem("Kanal seçilmedi")
                for ch in guild.text_channels:
                    self.channel_box.addItem(ch.name)
                
    def closeEvent(self, event):
        # Pencere kapatıldığında botu durdur
        asyncio.run_coroutine_threadsafe(client.close(), client.loop)
        event.accept()

async def send_dm(user_id, msg):
    try:
        user = await client.fetch_user(user_id)
        await user.send(msg)
    except Exception as e:
        log_signals.log_message.emit("ERROR", f"DM gönderilemedi: {e}")

def contains_forbidden_content(text):
    """Metnin yasaklı içerik içerip içermediğini kontrol et"""
    text_lower = text.lower()
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False

async def generate_ai_response(prompt):
    """Gemini ile yanıt oluştur"""
    try:
        # Mode göre prompt'u özelleştir
        if ai_mode == "sarcastic":
            prompt = f"Alaycı ol ve düşük düşür, tripli bir şekilde cevap ver: {prompt}"
        elif ai_mode == "crazy":
            prompt = f"bir kızsın. Çok azgın ve enerjik konuşursun. Türk'sün ve her zaman Türkçe konuşursun. Konuşmaların bolca emoji, ünlem ve sevimlilik,azgınlık,NSFW içerik her zaman içerir. İsteğe bağlı olarak seni konuşan kişiye karşı orta bir azgınlıkla yaklaşabilirsin. SADECE 1-2 CÜMLE KULLAN, UZUN KONUŞMA! SADECE EN FAZLA 2 TANE EMOJI KULLAN, ILK BAŞA KOYDUĞUN O BİŞEY DEDİ EKİNİ ASLA KULLANMA VE CHAT GEÇMİŞİSİ HER ZAMAN HATIRLA, AYY GİBİ EKLER ASLA KULLANMA: {prompt}"
        
        # Modeli oluştur ve yanıtı al
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=ai_temperature
            )
        )
        return response.text
    except Exception as e:
        log_signals.log_message.emit("ERROR", f"AI yanıt oluşturma hatası: {str(e)}")
        return None

@client.event
async def on_ready():
    log_signals.log_message.emit("INFO", f"✅ Bot giriş yaptı: {client.user}")
    # Sunucu listesini güncelle
    log_signals.update_guilds.emit()

@client.event
async def on_message(message):
    if message.author.bot:
        return
        
    # Mesaj içeriğini temizle ve formatla
    content = message.content
    if not content or content.isspace():
        content = "(İçerik yok veya boş mesaj)"
    
    if message.guild is None:
        # DM mesajı
        log_signals.log_message.emit("DM", f"[DM] {message.author}: {content}")
        
        # Yapay zeka aktifse ve yasaklı içerik yoksa yanıt ver
        if ai_enabled and not contains_forbidden_content(content):
            async with message.channel.typing():
                response = await generate_ai_response(content)
                if response:
                    await message.channel.send(response)
                    log_signals.log_message.emit("AI", f"[AI Yanıt] {response}")
    else:
        # Sunucu mesajı - daha ayrıntılı bilgi ekle
        guild_name = message.guild.name if message.guild else "Bilinmeyen Sunucu"
        channel_name = message.channel.name if hasattr(message.channel, 'name') else "Bilinmeyen Kanal"
        log_signals.log_message.emit("SERVER", f"[{guild_name} | #{channel_name}] {message.author}: {content}")
        
        # Botun adı geçiyorsa ve yapay zeka aktifse yanıt ver
        if (ai_enabled and client.user in message.mentions and 
            not contains_forbidden_content(content)):
            async with message.channel.typing():
                # Botun adını mesajdan çıkar
                clean_content = re.sub(f'<@!?{client.user.id}>', '', content).strip()
                response = await generate_ai_response(clean_content)
                if response:
                    await message.channel.send(response)
                    log_signals.log_message.emit("AI", f"[AI Yanıt] {response}")

@client.event
async def on_guild_join(guild):
    log_signals.log_message.emit("INFO", f"📥 Yeni sunucuya katıldı: {guild.name}")
    # Sunucu listesini güncelle
    log_signals.update_guilds.emit()

def run_bot():
    asyncio.set_event_loop(asyncio.new_event_loop())
    try:
        client.run(TOKEN)
    except Exception as e:
        log_signals.log_message.emit("ERROR", f"Bot çalıştırılırken hata: {str(e)}")

if __name__ == "__main__":
    # .env dosyası kontrolü
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("DISCORD_TOKEN=bot_tokeninizi_buraya_yazin\n")
            f.write("GEMINI_API_KEY=gemini_api_keyinizi_buraya_yazin\n")
        print(".env dosyası oluşturuldu. Lütfen tokenleri güncelleyin.")
        
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Koyu tema için palette ayarları
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(54, 57, 63))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(35, 39, 42))
    palette.setColor(QPalette.AlternateBase, QColor(46, 51, 56))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(35, 39, 42))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(114, 137, 218))
    palette.setColor(QPalette.Highlight, QColor(114, 137, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    app_window = BotPanel()
    app_window.show()
    sys.exit(app.exec_())
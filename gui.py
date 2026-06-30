#!/usr/bin/env python3
"""GUI клиент на PyQt5"""

import sys
import os
import asyncio
from datetime import datetime

# === Настройка путей (работает при любом способе запуска) ===
if __name__ == '__main__':
    # При прямом запуске добавляем корень проекта в sys.path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
else:
    # При запуске как модуль (python -m client.gui)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

# Абсолютные импорты – работают всегда
from client.network import NetworkClient
from crypto import CryptoManager, KeyStore

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QListWidget, QLabel,
    QSplitter, QStatusBar, QInputDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont


class NetworkThread(QThread):
    message_received = pyqtSignal(dict)
    connection_changed = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self.client = NetworkClient()
        self.loop = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.client.on_message = lambda msg: self.message_received.emit(msg)
        self.client.on_connected = lambda msg: self.connection_changed.emit(True, "Подключен")
        self.client.on_disconnected = lambda msg: self.connection_changed.emit(False, msg)

        self.loop.run_forever()

    def connect(self, host, port, user_id):
        self.loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self.client.connect(host, port, user_id))
        )

    def send(self, msg_type, data):
        self.loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self.client.send(msg_type, data))
        )

    def stop(self):
        self.loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self.client.close())
        )
        self.loop.call_soon_threadsafe(self.loop.stop)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Carrier Pigeon")
        self.setMinimumSize(800, 600)

        self.network = NetworkThread()
        self.crypto = CryptoManager()
        self.key_store = KeyStore()
        self.current_chat = None

        self._setup_ui()
        self._connect_signals()

        self.network.start()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # Левая панель
        left = QWidget()
        left_layout = QVBoxLayout(left)

        self.status_label = QLabel("Не подключен")
        left_layout.addWidget(self.status_label)

        self.contacts_list = QListWidget()
        left_layout.addWidget(self.contacts_list)

        self.connect_btn = QPushButton("Подключиться")
        self.connect_btn.clicked.connect(self._connect)
        left_layout.addWidget(self.connect_btn)

        # Правая панель
        right = QWidget()
        right_layout = QVBoxLayout(right)

        self.chat_header = QLabel("Выберите контакт")
        self.chat_header.setFont(QFont("Arial", 14, QFont.Bold))
        right_layout.addWidget(self.chat_header)

        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        right_layout.addWidget(self.chat_view)

        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Сообщение...")
        self.message_input.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.message_input)

        send_btn = QPushButton("Отправить")
        send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(send_btn)

        right_layout.addLayout(input_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        layout.addWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _connect_signals(self):
        self.network.connection_changed.connect(self._on_connection)
        self.network.message_received.connect(self._on_message)
        self.contacts_list.itemClicked.connect(self._on_contact_clicked)

    def _connect(self):
        host, ok = QInputDialog.getText(self, "Подключение", "IP сервера:")
        if not ok: return

        user_id, ok = QInputDialog.getText(self, "Подключение", "Ваш ID:")
        if not ok: return

        self.network.connect(host, 8080, user_id)

    def _on_connection(self, connected, message):
        self.status_label.setText(message if connected else "Не подключен")
        self.status_bar.showMessage(message)

    def _on_message(self, msg):
        if msg.get('type') == 'message':
            sender = msg.get('from', '?')
            text = msg.get('data', '')

            key = self.key_store.get_key(sender)
            if not key:
                key = b'\x00' * 32  # Тестовый ключ
                self.key_store.save_key(sender, key)

            decrypted = self.crypto.decrypt(text, key) or text

            if sender == self.current_chat or not self.current_chat:
                self.chat_view.append(f"{sender}: {decrypted}")

    def _on_contact_clicked(self, item):
        self.current_chat = item.text()
        self.chat_header.setText(f"Чат с {self.current_chat}")

    def _send_message(self):
        if not self.current_chat:
            QMessageBox.warning(self, "Ошибка", "Выберите контакт")
            return

        text = self.message_input.text().strip()
        if not text:
            return

        key = self.key_store.get_key(self.current_chat)
        if not key:
            key = b'\x00' * 32
            self.key_store.save_key(self.current_chat, key)

        encrypted = self.crypto.encrypt(text, key)
        self.network.send('message', {'to': self.current_chat, 'data': encrypted})

        self.chat_view.append(f"Вы: {text}")
        self.message_input.clear()

    def closeEvent(self, event):
        self.network.stop()
        self.network.wait()
        event.accept()


def main():
    # Для Windows обязательно
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
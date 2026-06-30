"""Сетевой модуль клиента"""

import asyncio
import json
import socket
import sys
import os
from typing import Callable, Optional

# === Настройка путей для возможности импорта crypto из любого места ===
if __name__ != '__main__':
    # Когда запускается как модуль (python -m client...)
    # Добавляем корень проекта в sys.path, чтобы импорт crypto работал
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)  # на уровень выше client/
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

# Абсолютный импорт (работает и при -m, и при прямом запуске)
from crypto import CryptoManager, KeyStore


class NetworkClient:
    def __init__(self):
        self.reader = None
        self.writer = None
        self.user_id = None
        self.running = False
        self.on_message: Optional[Callable] = None
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None

    async def connect(self, host: str, port: int, user_id: str) -> bool:
        try:
            self.reader, self.writer = await asyncio.open_connection(host, port)

            # УСКОРЕНИЕ: отключаем алгоритм Нейгла
            sock = self.writer.get_extra_info('socket')
            if sock:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            auth = json.dumps({'auth': user_id})
            self.writer.write((auth + '\n').encode())
            await self.writer.drain()

            response = await self.reader.readline()
            msg = json.loads(response.decode())

            if msg.get('type') == 'welcome':
                self.user_id = user_id
                self.running = True
                if self.on_connected:
                    self.on_connected(msg)
                asyncio.create_task(self._listen())
                return True

            return False
        except Exception as e:
            if self.on_disconnected:
                self.on_disconnected(str(e))
            return False

    async def _listen(self):
        while self.running:
            try:
                data = await self.reader.readline()
                if not data:
                    break
                msg = json.loads(data.decode())
                if self.on_message:
                    self.on_message(msg)
            except:
                break

        self.running = False
        if self.on_disconnected:
            self.on_disconnected("Соединение потеряно")

    async def send(self, msg_type: str, data: dict):
        if not self.writer:
            return
        data['type'] = msg_type
        self.writer.write((json.dumps(data) + '\n').encode())
        await self.writer.drain()

    async def close(self):
        self.running = False
        if self.writer:
            self.writer.close()
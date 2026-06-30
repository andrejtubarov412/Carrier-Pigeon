"""Конфигурация сервера"""

import os
from pathlib import Path

# Сеть
HOST = os.getenv('CARRIER_PIGEON_HOST', '0.0.0.0')
TCP_PORT = int(os.getenv('CARRIER_PIGEON_PORT', '8080'))

# Лимиты
MAX_CLIENTS = int(os.getenv('CARRIER_PIGEON_MAX_CLIENTS', '256'))
MAX_GROUP_MEMBERS = int(os.getenv('CARRIER_PIGEON_MAX_GROUP_MEMBERS', '50'))

# Таймауты (секунды)
AUTH_TIMEOUT = 10
CONNECTION_TIMEOUT = 60
CLEANUP_INTERVAL = 300
SAVE_INTERVAL = 300

# Хранилище
STATE_DIR = Path(os.getenv('CARRIER_PIGEON_STATE_DIR', './server_state'))
OFFLINE_QUEUE_MAX = 1000

# Логирование
LOG_LEVEL = os.getenv('CARRIER_PIGEON_LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('CARRIER_PIGEON_LOG_FILE', 'carrier_pigeon_server.log')
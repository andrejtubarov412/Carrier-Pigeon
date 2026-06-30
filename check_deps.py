#!/usr/bin/env python3
"""Проверка зависимостей Carrier Pigeon Messenger"""

import sys

CHECKS = {
    'asyncio': 'Сетевое взаимодействие',
    'json': 'Обработка JSON',
    'cryptography': 'Криптография',
    'PyQt5': 'Графический интерфейс',
}

OPTIONAL = {
    'pyaudio': 'Голосовые звонки',
    'cv2': 'Видео звонки',
    'numpy': 'Обработка аудио/видео',
}


def main():
    print("Проверка зависимостей Carrier Pigeon Messenger\n")

    all_ok = True

    for module, description in CHECKS.items():
        try:
            __import__(module)
            print(f"✓ {description} ({module})")
        except ImportError:
            print(f"❌ {description} ({module}) - ТРЕБУЕТСЯ")
            all_ok = False

    print("\nОпциональные:")
    for module, description in OPTIONAL.items():
        try:
            __import__(module)
            print(f"✓ {description} ({module})")
        except ImportError:
            print(f"⚠ {description} ({module}) - опционально")

    if all_ok:
        print("\n✓ Все основные зависимости установлены")
    else:
        print("\n❌ Установите отсутствующие зависимости:")
        print("  pip install -r requirements.txt")


if __name__ == '__main__':
    main()
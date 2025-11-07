#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Главная точка входа
Версия: 0.1.0
Компания: ООО "НПА Вира-Реалтайм"
"""

from __future__ import print_function
import sys
import os

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_VERSION, APP_NAME, APP_DESCRIPTION

def main():
    """Главная функция"""
    print("=" * 60)
    print(f"{APP_NAME} v{APP_VERSION}")
    print(APP_DESCRIPTION)
    print("=" * 60)
    print()
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "--version" or command == "-v":
            print(f"Версия: {APP_VERSION}")
            return
        
        if command == "--help" or command == "-h":
            print_help()
            return
    
    # По умолчанию запускаем GUI (если доступен)
    try:
        from gui.main_window import MainWindow
        print("[INFO] Запуск GUI режима...")
        app = MainWindow()
        app.run()
    except ImportError:
        print("[WARNING] GUI недоступен, запуск консольного режима...")
        print("[INFO] Консольный режим будет реализован позже")
        print_help()

def print_help():
    """Вывод справки"""
    print("Использование:")
    print("  python main.py              - Запуск GUI")
    print("  python main.py --help       - Показать справку")
    print("  python main.py --version    - Показать версию")
    print()
    print("Дополнительные команды:")
    print("  python rebuild.py           - Разборка проекта")
    print("  python build.py             - Сборка проекта")
    print("  python dist.py              - Создание дистрибутива")

if __name__ == '__main__':
    main()


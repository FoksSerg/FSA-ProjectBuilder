#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Тесты парсера
Версия: 0.1.0
"""

from __future__ import print_function
import sys
import os
import tempfile

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parser import CodeParser, parse_file


def test_simple_file():
    """Тест парсинга простого файла"""
    # Создаем временный файл для теста
    test_code = '''
"""Тестовый модуль"""
import os
import sys

CONSTANT = "test"

def test_function():
    """Тестовая функция"""
    pass

class TestClass:
    """Тестовый класс"""
    def __init__(self):
        pass
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_code)
        temp_path = f.name
    
    try:
        parser = CodeParser(temp_path)
        assert parser.parse(), "Парсинг должен быть успешным"
        
        structure = parser.get_structure()
        
        # Проверяем структуру
        assert 'classes' in structure
        assert 'functions' in structure
        assert 'imports' in structure
        assert 'constants' in structure
        
        # Проверяем класс
        classes = structure['classes']
        assert len(classes) == 1
        assert classes[0]['name'] == 'TestClass'
        
        # Проверяем функцию
        functions = structure['functions']
        assert len(functions) == 1
        assert functions[0]['name'] == 'test_function'
        
        # Проверяем импорты
        imports = structure['imports']
        assert len(imports) >= 2
        
        print("[OK] Тест парсинга простого файла пройден")
        
    finally:
        os.unlink(temp_path)


def test_parse_file_function():
    """Тест функции parse_file"""
    test_code = '''
class Test:
    pass
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_code)
        temp_path = f.name
    
    try:
        structure = parse_file(temp_path)
        assert structure is not None
        assert len(structure['classes']) == 1
        print("[OK] Тест функции parse_file пройден")
        
    finally:
        os.unlink(temp_path)


if __name__ == '__main__':
    print("Запуск тестов парсера...")
    print()
    
    try:
        test_simple_file()
        test_parse_file_function()
        
        print()
        print("=" * 60)
        print("[SUCCESS] Все тесты парсера пройдены успешно!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"[ERROR] Тест не пройден: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


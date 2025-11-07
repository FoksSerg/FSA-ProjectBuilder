#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Интеграционные тесты: разборка и сборка
"""

import os
import sys
import tempfile
import shutil
import unittest
import difflib

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rebuilder import rebuild_file
from core.builder import build_modules


class TestIntegration(unittest.TestCase):
    """Интеграционные тесты"""
    
    def setUp(self):
        """Подготовка тестового окружения"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, 'test_file.py')
        
        # Создаем тестовый файл
        test_code = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тестовый файл для интеграционного теста
"""

import os
import sys

APP_VERSION = "1.0.0"
APP_NAME = "TestApp"

class TestClass:
    """Тестовый класс"""
    
    def __init__(self):
        self.value = 10
    
    def get_value(self):
        return self.value

def test_function():
    """Тестовая функция"""
    return "test"

if __name__ == '__main__':
    print("Test")
'''
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write(test_code)
    
    def tearDown(self):
        """Очистка после тестов"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_rebuild_and_build(self):
        """Тест: разборка и сборка должны работать"""
        # Разбираем файл
        modules_dir = os.path.join(self.test_dir, 'modules')
        result = rebuild_file(self.test_file, modules_dir)
        self.assertTrue(result, "Разборка должна быть успешной")
        
        # Собираем обратно
        output_file = os.path.join(self.test_dir, 'test_built.py')
        result = build_modules(modules_dir, output_file)
        self.assertTrue(result, "Сборка должна быть успешной")
        
        # Проверяем, что файл создан
        self.assertTrue(os.path.exists(output_file), "Собранный файл должен существовать")
        
        # Проверяем синтаксис
        import py_compile
        try:
            py_compile.compile(output_file, doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"Собранный файл содержит синтаксические ошибки: {e}")
    
    def test_rebuild_build_roundtrip(self):
        """Тест: разборка и сборка должны сохранять основные элементы"""
        # Разбираем файл
        modules_dir = os.path.join(self.test_dir, 'modules')
        rebuild_file(self.test_file, modules_dir)
        
        # Собираем обратно
        output_file = os.path.join(self.test_dir, 'test_built.py')
        build_modules(modules_dir, output_file)
        
        # Читаем оригинальный и собранный файлы
        with open(self.test_file, 'r', encoding='utf-8') as f:
            original = f.read()
        
        with open(output_file, 'r', encoding='utf-8') as f:
            built = f.read()
        
        # Проверяем наличие основных элементов
        self.assertIn('APP_VERSION', built)
        self.assertIn('TestClass', built)
        self.assertIn('test_function', built)


if __name__ == '__main__':
    unittest.main()


#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тесты для сборки модулей в один файл
"""

import os
import sys
import tempfile
import shutil
import unittest

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.builder import Builder, build_modules
from core.rebuilder import rebuild_file


class TestBuild(unittest.TestCase):
    """Тесты для сборки модулей"""
    
    def setUp(self):
        """Подготовка тестового окружения"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, 'test_file.py')
        
        # Создаем тестовый файл
        test_code = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тестовый файл
"""

APP_VERSION = "1.0.0"
APP_NAME = "TestApp"

class TestClass:
    """Тестовый класс"""
    
    def __init__(self):
        self.value = 10

def test_function():
    """Тестовая функция"""
    return "test"
'''
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write(test_code)
        
        # Разбираем файл на модули
        self.modules_dir = os.path.join(self.test_dir, 'modules')
        rebuild_file(self.test_file, self.modules_dir)
    
    def tearDown(self):
        """Очистка после тестов"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_build_modules(self):
        """Тест сборки модулей"""
        output_file = os.path.join(self.test_dir, 'test_built.py')
        result = build_modules(self.modules_dir, output_file)
        
        self.assertTrue(result, "Сборка должна быть успешной")
        self.assertTrue(os.path.exists(output_file), "Выходной файл должен быть создан")
        
        # Проверяем содержимое файла
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('APP_VERSION', content)
        self.assertIn('TestClass', content)
        self.assertIn('test_function', content)
    
    def test_build_syntax(self):
        """Тест синтаксиса собранного файла"""
        output_file = os.path.join(self.test_dir, 'test_built.py')
        build_modules(self.modules_dir, output_file)
        
        # Проверяем синтаксис
        import py_compile
        try:
            py_compile.compile(output_file, doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"Собранный файл содержит синтаксические ошибки: {e}")


if __name__ == '__main__':
    unittest.main()


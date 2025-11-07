#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тесты для разборки файлов на модули
"""

import os
import sys
import tempfile
import shutil
import unittest

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rebuilder import Rebuilder, rebuild_file


class TestRebuild(unittest.TestCase):
    """Тесты для разборки файлов"""
    
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
    
    def test_rebuild_file(self):
        """Тест разборки файла"""
        output_dir = os.path.join(self.test_dir, 'modules')
        result = rebuild_file(self.test_file, output_dir)
        
        self.assertTrue(result, "Разборка должна быть успешной")
        self.assertTrue(os.path.exists(output_dir), "Директория модулей должна быть создана")
        
        # Проверяем наличие config.py
        config_file = os.path.join(output_dir, 'config.py')
        self.assertTrue(os.path.exists(config_file), "config.py должен быть создан")
        
        # Проверяем наличие метаданных
        metadata_dir = os.path.join(output_dir, '.metadata')
        self.assertTrue(os.path.exists(metadata_dir), "Директория метаданных должна быть создана")
    
    def test_rebuild_structure(self):
        """Тест структуры разборки"""
        output_dir = os.path.join(self.test_dir, 'modules')
        rebuild_file(self.test_file, output_dir)
        
        # Проверяем наличие категорий
        categories = ['core', 'gui', 'utils', 'models', 'analyzers']
        for category in categories:
            category_dir = os.path.join(output_dir, category)
            self.assertTrue(os.path.exists(category_dir), f"Категория {category} должна быть создана")
    
    def test_rebuild_metadata(self):
        """Тест метаданных"""
        output_dir = os.path.join(self.test_dir, 'modules')
        rebuild_file(self.test_file, output_dir)
        
        metadata_file = os.path.join(output_dir, '.metadata', 'metadata.json')
        self.assertTrue(os.path.exists(metadata_file), "Файл метаданных должен быть создан")
        
        import json
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        self.assertIn('source_file', metadata)
        self.assertIn('total_classes', metadata)
        self.assertIn('total_functions', metadata)


if __name__ == '__main__':
    unittest.main()


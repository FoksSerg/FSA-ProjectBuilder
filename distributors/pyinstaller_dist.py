#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - PyInstaller дистрибутор
Версия: 0.1.0
Компания: ООО "НПА Вира-Реалтайм"
"""

from __future__ import print_function
import os
import shutil
from typing import Dict, List, Optional, Any
from .base import BaseDistributor


class PyInstallerDistributor(BaseDistributor):
    """Создание дистрибутивов с помощью PyInstaller"""
    
    def __init__(self, project_dir: str, output_dir: Optional[str] = None):
        super().__init__(project_dir, output_dir)
        self.name = "PyInstaller"
    
    def is_available(self) -> bool:
        """Проверка доступности PyInstaller"""
        try:
            import PyInstaller
            return True
        except ImportError:
            return False
    
    def get_command(self, main_file: str, config: Optional[Dict[str, Any]] = None) -> List[str]:
        """Получение команды для сборки"""
        if config is None:
            config = {}
        
        command = ['pyinstaller']
        
        # Основные опции
        if config.get('onefile', True):
            command.append('--onefile')
        
        if config.get('windowed', False):
            command.append('--windowed')
        elif config.get('noconsole', False):
            command.append('--noconsole')
        
        # Имя выходного файла
        if 'name' in config:
            command.extend(['--name', config['name']])
        
        # Иконка
        if 'icon' in config:
            command.extend(['--icon', config['icon']])
        
        # Дополнительные файлы
        if 'add_data' in config:
            for src, dst in config['add_data']:
                command.extend(['--add-data', f"{src}{os.pathsep}{dst}"])
        
        # Скрытые импорты
        if 'hidden_imports' in config:
            for imp in config['hidden_imports']:
                command.extend(['--hidden-import', imp])
        
        # Выходная директория
        command.extend(['--distpath', self.output_dir])
        
        # Временная директория
        if 'workpath' in config:
            command.extend(['--workpath', config['workpath']])
        
        # Спецификация
        if 'spec' in config:
            command.append(config['spec'])
        else:
            command.append(main_file)
        
        return command
    
    def create_distribution(self, main_file: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Создание дистрибутива"""
        if not self.is_available():
            print(f"[{self.name}] PyInstaller не установлен. Установите его: pip install pyinstaller")
            return False
        
        if not self.prepare_output_dir():
            return False
        
        main_file_path = os.path.join(self.project_dir, main_file)
        if not os.path.exists(main_file_path):
            print(f"[{self.name}] Файл не найден: {main_file_path}")
            return False
        
        command = self.get_command(main_file, config)
        return self.run_command(command)


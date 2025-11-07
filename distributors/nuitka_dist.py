#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Nuitka дистрибутор
Версия: 0.1.0
Компания: ООО "НПА Вира-Реалтайм"
"""

from __future__ import print_function
import os
from typing import Dict, List, Optional, Any
from .base import BaseDistributor


class NuitkaDistributor(BaseDistributor):
    """Создание дистрибутивов с помощью Nuitka"""
    
    def __init__(self, project_dir: str, output_dir: Optional[str] = None):
        super().__init__(project_dir, output_dir)
        self.name = "Nuitka"
    
    def is_available(self) -> bool:
        """Проверка доступности Nuitka"""
        try:
            import nuitka
            return True
        except ImportError:
            # Nuitka может быть установлен как команда, но не как модуль
            import shutil
            return shutil.which('nuitka') is not None
    
    def get_command(self, main_file: str, config: Optional[Dict[str, Any]] = None) -> List[str]:
        """Получение команды для сборки"""
        command = ['nuitka']
        
        if config:
            if config.get('standalone', True):
                command.append('--standalone')
            
            if config.get('onefile', False):
                command.append('--onefile')
            
            if config.get('windows_icon_from_ico', None):
                command.extend(['--windows-icon-from-ico', config['windows_icon_from_ico']])
            
            if config.get('output_dir', None):
                command.extend(['--output-dir', config['output_dir']])
            else:
                command.extend(['--output-dir', self.output_dir])
            
            if 'include_modules' in config:
                for mod in config['include_modules']:
                    command.extend(['--include-module', mod])
            
            if 'nofollow_imports' in config and config['nofollow_imports']:
                command.append('--nofollow-imports')
        
        command.append(main_file)
        return command
    
    def create_distribution(self, main_file: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Создание дистрибутива"""
        if not self.is_available():
            print(f"[{self.name}] Nuitka не установлен. Установите его: pip install nuitka")
            return False
        
        if not self.prepare_output_dir():
            return False
        
        main_file_path = os.path.join(self.project_dir, main_file)
        if not os.path.exists(main_file_path):
            print(f"[{self.name}] Файл не найден: {main_file_path}")
            return False
        
        command = self.get_command(main_file, config)
        return self.run_command(command)


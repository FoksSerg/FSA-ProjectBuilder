#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - cx_Freeze дистрибутор
Версия: 0.1.0
Компания: ООО "НПА Вира-Реалтайм"
"""

from __future__ import print_function
import os
from typing import Dict, List, Optional, Any
from .base import BaseDistributor


class CxFreezeDistributor(BaseDistributor):
    """Создание дистрибутивов с помощью cx_Freeze"""
    
    def __init__(self, project_dir: str, output_dir: Optional[str] = None):
        super().__init__(project_dir, output_dir)
        self.name = "cx_Freeze"
    
    def is_available(self) -> bool:
        """Проверка доступности cx_Freeze"""
        try:
            import cx_Freeze
            return True
        except ImportError:
            return False
    
    def get_command(self, main_file: str, config: Optional[Dict[str, Any]] = None) -> List[str]:
        """Получение команды для сборки"""
        command = ['cxfreeze', main_file]
        
        if config:
            if 'target_name' in config:
                command.extend(['--target-name', config['target_name']])
            
            if 'target_dir' in config:
                command.extend(['--target-dir', config['target_dir']])
            else:
                command.extend(['--target-dir', self.output_dir])
            
            if 'includes' in config:
                for inc in config['includes']:
                    command.extend(['--include-modules', inc])
            
            if 'excludes' in config:
                for exc in config['excludes']:
                    command.extend(['--exclude-modules', exc])
        
        return command
    
    def create_distribution(self, main_file: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Создание дистрибутива"""
        if not self.is_available():
            print(f"[{self.name}] cx_Freeze не установлен. Установите его: pip install cx_Freeze")
            return False
        
        if not self.prepare_output_dir():
            return False
        
        main_file_path = os.path.join(self.project_dir, main_file)
        if not os.path.exists(main_file_path):
            print(f"[{self.name}] Файл не найден: {main_file_path}")
            return False
        
        command = self.get_command(main_file, config)
        return self.run_command(command)


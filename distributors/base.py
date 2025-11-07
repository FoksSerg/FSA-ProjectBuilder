#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Базовый класс для создания дистрибутивов
Версия: 0.1.0
Компания: ООО "НПА Вира-Реалтайм"
"""

from __future__ import print_function
import os
import subprocess
import shutil
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod


class BaseDistributor(ABC):
    """Базовый класс для создания дистрибутивов"""
    
    def __init__(self, project_dir: str, output_dir: Optional[str] = None):
        """
        Инициализация дистрибутора
        
        Args:
            project_dir: Директория проекта
            output_dir: Директория для выходных файлов (по умолчанию: project_dir/dist)
        """
        self.project_dir = os.path.abspath(project_dir)
        if output_dir:
            self.output_dir = os.path.abspath(output_dir)
        else:
            self.output_dir = os.path.join(self.project_dir, 'dist')
        
        self.name = self.__class__.__name__
        
    @abstractmethod
    def is_available(self) -> bool:
        """
        Проверка доступности инструмента
        
        Returns:
            bool: True если инструмент доступен, False если нет
        """
        pass
    
    @abstractmethod
    def create_distribution(self, main_file: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Создание дистрибутива
        
        Args:
            main_file: Главный файл проекта
            config: Конфигурация сборки
            
        Returns:
            bool: True если сборка успешна, False если ошибка
        """
        pass
    
    @abstractmethod
    def get_command(self, main_file: str, config: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Получение команды для сборки
        
        Args:
            main_file: Главный файл проекта
            config: Конфигурация сборки
            
        Returns:
            List[str]: Команда для выполнения
        """
        pass
    
    def run_command(self, command: List[str], cwd: Optional[str] = None) -> bool:
        """
        Выполнение команды
        
        Args:
            command: Команда для выполнения
            cwd: Рабочая директория
            
        Returns:
            bool: True если команда выполнена успешно, False если ошибка
        """
        try:
            print(f"[{self.name}] Выполнение команды: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=cwd or self.project_dir,
                check=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                print(f"[{self.name}] Вывод: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[{self.name}] Ошибка выполнения команды: {e}")
            if e.stderr:
                print(f"[{self.name}] Ошибка: {e.stderr}")
            return False
        except FileNotFoundError:
            print(f"[{self.name}] Команда не найдена. Убедитесь, что инструмент установлен.")
            return False
    
    def prepare_output_dir(self) -> bool:
        """Подготовка выходной директории"""
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            return True
        except Exception as e:
            print(f"[{self.name}] Ошибка создания выходной директории: {e}")
            return False


#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Сборка модулей в один файл
Сборка разобранных модулей обратно в единый файл
Версия: 0.1.0
Компания: ООО "НПА Вира-Реалтайм"
"""

from __future__ import print_function
import os
import json
import re
import time
from typing import Dict, List, Optional, Any
from .dependency_resolver import DependencyResolver
from config import DEFAULT_MODULES_DIR, DEFAULT_METADATA_DIR, BUILD_CONFIG


class Builder:
    """Сборка модулей в один файл"""
    
    def __init__(self, modules_dir: str, output_file: Optional[str] = None):
        """
        Инициализация сборщика
        
        Args:
            modules_dir: Директория с модулями
            output_file: Путь к выходному файлу (по умолчанию: modules_dir + "_built.py")
        """
        self.modules_dir = os.path.abspath(modules_dir)
        self.metadata_dir = os.path.join(self.modules_dir, DEFAULT_METADATA_DIR)
        
        if output_file:
            self.output_file = os.path.abspath(output_file)
        else:
            # По умолчанию создаем файл рядом с директорией модулей
            parent_dir = os.path.dirname(self.modules_dir)
            dir_name = os.path.basename(self.modules_dir)
            self.output_file = os.path.join(parent_dir, f"{dir_name}_built.py")
        
        self.metadata = None
        self.modules_order = []
        self.imports_collected = set()
        
    def build(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Сборка модулей в один файл
        
        Args:
            config: Конфигурация сборки (по умолчанию из BUILD_CONFIG)
        
        Returns:
            bool: True если сборка успешна, False если ошибка
        """
        if config is None:
            config = BUILD_CONFIG
        
        print(f"[BUILD] Начало сборки модулей из: {self.modules_dir}")
        print(f"[BUILD] Выходной файл: {self.output_file}")
        
        # 1. Загружаем метаданные
        print("[BUILD] Загрузка метаданных...")
        if not self._load_metadata():
            print("[WARNING] Метаданные не найдены, используем автоматическое определение порядка")
        
        # 2. Определяем порядок загрузки модулей
        print("[BUILD] Определение порядка загрузки модулей...")
        if not self._determine_load_order():
            print("[ERROR] Ошибка определения порядка загрузки")
            return False
        
        # 3. Собираем код из модулей
        print("[BUILD] Сборка кода из модулей...")
        code_parts = self._collect_code_parts()
        
        # 4. Объединяем код
        print("[BUILD] Объединение кода...")
        combined_code = self._combine_code(code_parts, config)
        
        # 5. Применяем настройки (очистка, оптимизация)
        if config:
            print("[BUILD] Применение настроек...")
            combined_code = self._apply_config(combined_code, config)
        
        # 6. Сохраняем результат
        print("[BUILD] Сохранение результата...")
        if not self._save_output(combined_code):
            print("[ERROR] Ошибка сохранения результата")
            return False
        
        print(f"[SUCCESS] Сборка завершена успешно!")
        print(f"[INFO] Файл создан: {self.output_file}")
        return True
    
    def _load_metadata(self) -> bool:
        """Загрузка метаданных"""
        try:
            metadata_path = os.path.join(self.metadata_dir, 'metadata.json')
            if not os.path.exists(metadata_path):
                return False
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            
            return True
        except Exception as e:
            print(f"[WARNING] Ошибка загрузки метаданных: {e}")
            return False
    
    def _determine_load_order(self) -> bool:
        """Определение порядка загрузки модулей"""
        try:
            # Собираем все модули
            all_modules = []
            
            # Сканируем директорию модулей
            for root, dirs, files in os.walk(self.modules_dir):
                # Пропускаем метаданные и __pycache__
                if DEFAULT_METADATA_DIR in root or '__pycache__' in root:
                    continue
                
                for file in files:
                    if file.endswith('.py') and file != '__init__.py':
                        module_path = os.path.join(root, file)
                        rel_path = os.path.relpath(module_path, self.modules_dir)
                        all_modules.append(rel_path)
            
            # Если есть метаданные, используем их для определения порядка
            if self.metadata and 'module_mapping' in self.metadata:
                # Используем порядок из метаданных
                # Упрощенная версия - просто сортируем по имени
                self.modules_order = sorted(all_modules)
            else:
                # Автоматическое определение порядка
                # Сначала config.py, imports.py, затем по категориям
                priority_files = ['config.py', 'imports.py']
                other_modules = [m for m in all_modules if m not in priority_files]
                
                self.modules_order = []
                for priority in priority_files:
                    if priority in all_modules:
                        self.modules_order.append(priority)
                
                # Добавляем остальные модули, отсортированные по категориям
                category_order = ['core', 'handlers', 'managers', 'gui', 'utils', 'models', 'analyzers', 'logging']
                for category in category_order:
                    category_modules = [m for m in other_modules if m.startswith(category + '/')]
                    self.modules_order.extend(sorted(category_modules))
                
                # Добавляем остальные модули
                remaining = [m for m in other_modules if m not in self.modules_order]
                self.modules_order.extend(sorted(remaining))
            
            print(f"[BUILD] Найдено модулей: {len(self.modules_order)}")
            if len(self.modules_order) == 0:
                print(f"[WARNING] Модули не найдены в директории: {self.modules_dir}")
                print(f"[WARNING] Проверьте, что директория содержит .py файлы (кроме __init__.py)")
            else:
                print(f"[BUILD] Модули для сборки: {self.modules_order[:5]}...")  # Показываем первые 5
            return True
        except Exception as e:
            print(f"[ERROR] Ошибка определения порядка: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _collect_code_parts(self) -> List[Dict[str, Any]]:
        """Сборка частей кода из модулей"""
        code_parts = []
        
        if not self.modules_order:
            print("[WARNING] Список модулей пуст, нечего собирать")
            print("[WARNING] Проверьте, что директория содержит .py файлы (кроме __init__.py)")
            return code_parts
        
        print(f"[BUILD] Сборка кода из {len(self.modules_order)} модулей...")
        
        for module_path in self.modules_order:
            full_path = os.path.join(self.modules_dir, module_path)
            
            if not os.path.exists(full_path):
                print(f"[WARNING] Модуль не найден: {module_path}")
                continue
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Извлекаем импорты и код
                imports, code = self._extract_imports_and_code(content)
                
                code_parts.append({
                    'path': module_path,
                    'imports': imports,
                    'code': code
                })
                
                # Собираем импорты
                self.imports_collected.update(imports)
                
            except Exception as e:
                print(f"[WARNING] Ошибка чтения модуля {module_path}: {e}")
                continue
        
        return code_parts
    
    def _extract_imports_and_code(self, content: str) -> tuple:
        """
        Извлечение импортов и кода из модуля
        
        Returns:
            tuple: (imports_list, code_without_imports)
        """
        lines = content.split('\n')
        imports = []
        code_lines = []
        in_docstring = False
        docstring_char = None
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Пропускаем shebang и encoding
            if i == 0 and (stripped.startswith('#!') or stripped.startswith('# -*-')):
                i += 1
                continue
            
            # Обработка docstrings
            if '"""' in line or "'''" in line:
                if not in_docstring:
                    # Начало docstring
                    in_docstring = True
                    if '"""' in line:
                        docstring_char = '"""'
                    else:
                        docstring_char = "'''"
                else:
                    # Конец docstring
                    if docstring_char in line:
                        in_docstring = False
                        docstring_char = None
            
            # Собираем импорты (только если не в docstring)
            if not in_docstring:
                if stripped.startswith('import ') or stripped.startswith('from '):
                    imports.append(line)
                    i += 1
                    continue
            
            # Остальной код
            code_lines.append(line)
            i += 1
        
        code = '\n'.join(code_lines)
        return imports, code
    
    def _combine_code(self, code_parts: List[Dict[str, Any]], config: Optional[Dict[str, Any]] = None) -> str:
        """Объединение кода из модулей"""
        # Заголовок файла
        header = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматически собранный файл из модулей
Сгенерировано FSA-ProjectBuilder
"""

'''
        
        if not code_parts:
            print("[WARNING] Нет частей кода для объединения, возвращаем только заголовок")
            print("[WARNING] Проверьте, что в директории есть .py файлы (кроме __init__.py)")
            return header
        
        print(f"[BUILD] Объединение {len(code_parts)} частей кода...")
        
        # Собираем все уникальные импорты
        all_imports = []
        seen_imports = set()
        
        for part in code_parts:
            for imp in part['imports']:
                # Нормализуем импорт для сравнения
                normalized = imp.strip()
                if normalized and normalized not in seen_imports:
                    seen_imports.add(normalized)
                    all_imports.append(imp)
        
        # Группируем импорты
        standard_imports = []
        third_party_imports = []
        local_imports = []
        
        for imp in all_imports:
            stripped = imp.strip()
            if stripped.startswith('from .') or stripped.startswith('import .'):
                # Локальные импорты - пропускаем (они будут заменены)
                continue
            elif any(module in stripped for module in ['os', 'sys', 'json', 're', 'typing', 'abc', 'collections', 'datetime', 'threading', 'queue', 'tempfile', 'shutil', 'subprocess', 'hashlib', 'time', 'traceback']):
                standard_imports.append(imp)
            elif any(module in stripped for module in ['tkinter', 'requests', 'psutil']):
                third_party_imports.append(imp)
            else:
                standard_imports.append(imp)
        
        # Сортируем импорты
        standard_imports = sorted(set(standard_imports))
        third_party_imports = sorted(set(third_party_imports))
        
        # Объединяем код
        combined = header
        
        # Добавляем импорты
        if standard_imports:
            combined += '\n'.join(standard_imports) + '\n\n'
        
        if third_party_imports:
            combined += '\n'.join(third_party_imports) + '\n\n'
        
        # Добавляем код из модулей
        code_sections = 0
        total_code_length = 0
        for part in code_parts:
            # Удаляем локальные импорты из кода
            code = part['code']
            code = re.sub(r'^from \. import .*$', '', code, flags=re.MULTILINE)
            code = re.sub(r'^from \.\w+ import .*$', '', code, flags=re.MULTILINE)
            
            if code.strip():  # Проверяем, что код не пустой
                # Добавляем разделитель
                combined += f"\n# ============================================================================\n"
                combined += f"# {part['path']}\n"
                combined += f"# ============================================================================\n\n"
                combined += code + '\n\n'
                code_sections += 1
                total_code_length += len(code)
            else:
                print(f"[WARNING] Модуль {part['path']} не содержит кода (только импорты)")
        
        if code_sections == 0:
            print("[WARNING] Код из модулей не найден, файл будет содержать только заголовок и импорты")
        else:
            print(f"[BUILD] Добавлено {code_sections} секций кода, всего {total_code_length} символов")
        
        print(f"[BUILD] Итоговый размер файла: {len(combined)} символов")
        return combined
    
    def _apply_config(self, code: str, config: Dict[str, Any]) -> str:
        """Применение настроек сборки"""
        # Очистка
        if config.get('cleanup', {}).get('remove_empty_lines', False):
            lines = code.split('\n')
            max_empty = config['cleanup'].get('max_empty_lines', 2)
            
            cleaned_lines = []
            empty_count = 0
            
            for line in lines:
                if not line.strip():
                    empty_count += 1
                    if empty_count <= max_empty:
                        cleaned_lines.append(line)
                else:
                    empty_count = 0
                    cleaned_lines.append(line)
            
            code = '\n'.join(cleaned_lines)
        
        # Удаление trailing whitespace
        if config.get('cleanup', {}).get('remove_trailing_whitespace', False):
            lines = code.split('\n')
            code = '\n'.join(line.rstrip() for line in lines)
        
        return code
    
    def _save_output(self, code: str) -> bool:
        """Сохранение результата"""
        try:
            # Проверяем абсолютный путь
            output_file_abs = os.path.abspath(self.output_file)
            output_dir = os.path.dirname(output_file_abs)
            
            print(f"[BUILD] Сохранение файла: {output_file_abs}")
            print(f"[BUILD] Директория выходного файла: {output_dir}")
            print(f"[BUILD] Размер кода: {len(code)} символов")
            
            # Проверяем, что директория существует
            if output_dir and not os.path.exists(output_dir):
                print(f"[BUILD] Создание директории: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
                if not os.path.exists(output_dir):
                    print(f"[ERROR] Не удалось создать директорию: {output_dir}")
                    return False
                print(f"[BUILD] Директория создана: {output_dir}")
            
            # Проверяем права на запись
            if not os.access(output_dir, os.W_OK):
                print(f"[ERROR] Нет прав на запись в директорию: {output_dir}")
                return False
            
            # Сохраняем файл
            print(f"[BUILD] Запись файла...")
            with open(output_file_abs, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Синхронизируем файловую систему
            time.sleep(0.1)  # Небольшая задержка для синхронизации
            
            # Проверяем, что файл создан
            if os.path.exists(output_file_abs):
                file_size = os.path.getsize(output_file_abs)
                print(f"[BUILD] Файл успешно сохранен: {output_file_abs}")
                print(f"[BUILD] Размер файла: {file_size} байт")
                print(f"[BUILD] Файл существует: {os.path.exists(output_file_abs)}")
                print(f"[BUILD] Полный путь: {os.path.abspath(output_file_abs)}")
                
                # Дополнительная проверка - читаем файл обратно
                try:
                    with open(output_file_abs, 'r', encoding='utf-8') as f:
                        read_size = len(f.read())
                    print(f"[BUILD] Размер прочитанного файла: {read_size} символов")
                    if read_size != len(code):
                        print(f"[WARNING] Размеры не совпадают: записано {len(code)}, прочитано {read_size}")
                except Exception as e:
                    print(f"[WARNING] Не удалось прочитать файл для проверки: {e}")
                
                # Проверяем содержимое директории
                if os.path.exists(output_dir):
                    files_in_dir = os.listdir(output_dir)
                    print(f"[BUILD] Файлы в директории: {files_in_dir}")
                    if os.path.basename(output_file_abs) not in files_in_dir:
                        print(f"[ERROR] Файл не найден в списке файлов директории!")
                        print(f"[ERROR] Ищем: {os.path.basename(output_file_abs)}")
                        print(f"[ERROR] В директории: {files_in_dir}")
                
                self.output_file = output_file_abs  # Обновляем путь на абсолютный
                return True
            else:
                print(f"[ERROR] Файл не найден после сохранения: {output_file_abs}")
                print(f"[ERROR] Директория существует: {os.path.exists(output_dir)}")
                if os.path.exists(output_dir):
                    files_in_dir = os.listdir(output_dir)
                    print(f"[ERROR] Содержимое директории: {files_in_dir}")
                else:
                    print(f"[ERROR] Директория не существует: {output_dir}")
                return False
            
        except PermissionError as e:
            print(f"[ERROR] Ошибка прав доступа при сохранении файла: {e}")
            print(f"[ERROR] Файл: {self.output_file}")
            print(f"[ERROR] Директория: {os.path.dirname(os.path.abspath(self.output_file))}")
            return False
        except Exception as e:
            import traceback
            print(f"[ERROR] Ошибка сохранения файла: {e}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return False


def build_modules(modules_dir: str, output_file: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Удобная функция для сборки модулей в один файл
    
    Args:
        modules_dir: Директория с модулями
        output_file: Путь к выходному файлу (опционально)
        config: Конфигурация сборки (опционально)
        
    Returns:
        bool: True если сборка успешна, False если ошибка
    """
    builder = Builder(modules_dir, output_file)
    return builder.build(config)


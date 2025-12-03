#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Главное окно GUI
Версия: 0.1.0
Автор: Фокин Сергей Александрович (@FoksSerg)
Компания: ООО "НПА Вира-Реалтайм"
"""

from __future__ import print_function
import sys
import os
import threading
import logging
import time
import json
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import Optional

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import APP_VERSION, APP_NAME, APP_DESCRIPTION, APP_AUTHOR


class MainWindow:
    """Главное окно приложения"""
    
    def __init__(self):
        """Инициализация главного окна"""
        self.root = None
        self.project_dir = None
        self.main_file = None
        self.output_dir = None
        self.status_text = None
        self.log_file = None
        self.logger = None
        self.preview_rebuild_text = None
        self.preview_build_text = None
        
        # Путь к файлу настроек
        self.settings_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".fsa_projectbuilder_settings.json"
        )
        
        self._init_logging()
        self._init_gui()
    
    def _init_logging(self):
        """Инициализация логирования в файл"""
        try:
            # Создаем папку Logs если её нет
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Logs")
            os.makedirs(logs_dir, exist_ok=True)
            
            # Создаем имя файла лога с датой и временем
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"fsa_projectbuilder_{timestamp}.log"
            self.log_file = os.path.join(logs_dir, log_filename)
            
            # Настраиваем логирование
            self.logger = logging.getLogger('FSA-ProjectBuilder')
            self.logger.setLevel(logging.DEBUG)
            
            # Обработчик для файла
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # Формат логов
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            
            self.logger.info(f"Инициализация {APP_NAME} v{APP_VERSION}")
            self.logger.info(f"Лог файл: {self.log_file}")
            
        except Exception as e:
            print(f"[WARNING] Не удалось инициализировать логирование: {e}")
            self.logger = None
    
    def _init_gui(self):
        """Инициализация GUI"""
        try:
            self.root = tk.Tk()
            self.root.title(f"{APP_NAME} v{APP_VERSION}")
            self.root.minsize(800, 600)
            
            # Инициализируем переменные после создания root
            self.project_dir = tk.StringVar()
            self.main_file = tk.StringVar(value="main.py")
            self.output_dir = tk.StringVar()
            self.status_text = tk.StringVar(value="Готов к работе")
            
            # Загружаем сохраненные настройки
            settings = self._load_settings()
            
            # Восстанавливаем размер и позицию окна
            if settings:
                geometry = settings.get('geometry', '1000x700')
                position = settings.get('position', None)
                if position:
                    geometry = f"{geometry}+{position['x']}+{position['y']}"
                self.root.geometry(geometry)
                
                # Восстанавливаем поля
                if settings.get('project_dir'):
                    self.project_dir.set(settings['project_dir'])
                if settings.get('main_file'):
                    self.main_file.set(settings['main_file'])
                if settings.get('output_dir'):
                    self.output_dir.set(settings['output_dir'])
            else:
                # Используем значения по умолчанию
                self.root.geometry("1000x700")
                self._center_window()
            
            # Добавляем отслеживание изменений полей для автосохранения
            self.project_dir.trace_add('write', lambda *args: self._save_settings_delayed())
            self.main_file.trace_add('write', lambda *args: self._save_settings_delayed())
            self.output_dir.trace_add('write', lambda *args: self._save_settings_delayed())
            
            # Делаем окно поверх всех на 3 секунды
            self.root.attributes('-topmost', True)
            self.root.after(3000, lambda: self.root.attributes('-topmost', False))
            
            # Обработчик закрытия окна
            self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
            
            # Отслеживаем изменение размера и позиции окна
            self.root.bind('<Configure>', self._on_window_configure)
            
            # Создаем меню
            self._create_menu()
            
            # Создаем основной интерфейс
            self._create_main_interface()
            
            # Если настройки не были загружены, центрируем окно
            if not settings:
                self._center_window()
            
        except ImportError as e:
            print(f"[ERROR] Ошибка импорта: {e}")
            sys.exit(1)
    
    def _create_menu(self):
        """Создание меню"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Выбрать проект...", command=self._select_project)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        
        # Меню "Операции"
        operations_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Операции", menu=operations_menu)
        operations_menu.add_command(label="Разборка на модули", command=self._rebuild_project)
        operations_menu.add_command(label="Сборка модулей", command=self._build_project)
        operations_menu.add_command(label="Создать дистрибутив", command=self._create_distribution)
        
        # Меню "Справка"
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self._show_about)
        help_menu.add_command(label="Документация", command=self._show_docs)
    
    def _create_main_interface(self):
        """Создание основного интерфейса"""
        # Главный контейнер
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Левая панель - настройки
        left_frame = ttk.LabelFrame(main_frame, text="Настройки проекта", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        left_frame.config(width=300)
        
        # Правая панель - логи и информация
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Настройки проекта
        self._create_project_settings(left_frame)
        
        # Логи и информация
        self._create_log_panel(right_frame)
        
        # Статусная строка
        self._create_status_bar()
    
    def _create_project_settings(self, parent):
        """Создание панели настроек проекта"""
        # Проект
        ttk.Label(parent, text="Директория проекта:").pack(anchor=tk.W, pady=(0, 5))
        project_frame = ttk.Frame(parent)
        project_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Entry(project_frame, textvariable=self.project_dir, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(project_frame, text="...", command=self._select_project, width=3).pack(side=tk.LEFT, padx=(5, 0))
        
        # Главный файл
        ttk.Label(parent, text="Главный файл:").pack(anchor=tk.W, pady=(0, 5))
        main_file_frame = ttk.Frame(parent)
        main_file_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Entry(main_file_frame, textvariable=self.main_file, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(main_file_frame, text="...", command=self._select_main_file, width=3).pack(side=tk.LEFT, padx=(5, 0))
        
        # Выходная директория
        ttk.Label(parent, text="Выходная директория:").pack(anchor=tk.W, pady=(0, 5))
        output_frame = ttk.Frame(parent)
        output_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Entry(output_frame, textvariable=self.output_dir, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="...", command=self._select_output_dir, width=3).pack(side=tk.LEFT, padx=(5, 0))
        
        # Разделитель
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Кнопки операций
        ttk.Button(parent, text="Разборка на модули", command=self._rebuild_project, width=30).pack(fill=tk.X, pady=5)
        ttk.Button(parent, text="Сборка модулей", command=self._build_project, width=30).pack(fill=tk.X, pady=5)
        ttk.Button(parent, text="Создать дистрибутив", command=self._create_distribution, width=30).pack(fill=tk.X, pady=5)
        
        # Информация
        info_frame = ttk.LabelFrame(parent, text="Информация", padding="10")
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(info_frame, text=f"Версия: {APP_VERSION}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Автор: {APP_AUTHOR}").pack(anchor=tk.W)
    
    def _create_log_panel(self, parent):
        """Создание панели логов"""
        # Вкладки
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Вкладка "Логи"
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="Логи")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20, width=60)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # Вкладка "Структура проекта"
        structure_frame = ttk.Frame(notebook)
        notebook.add(structure_frame, text="Структура проекта")
        
        # Создаем TreeView с прокруткой
        tree_frame = ttk.Frame(structure_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.structure_tree = ttk.Treeview(tree_frame, yscrollcommand=scrollbar.set)
        self.structure_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.structure_tree.yview)
        
        # Настраиваем колонки
        self.structure_tree["columns"] = ("type", "size")
        self.structure_tree.column("#0", width=300, anchor=tk.W)
        self.structure_tree.column("type", width=100, anchor=tk.W)
        self.structure_tree.column("size", width=80, anchor=tk.E)
        
        self.structure_tree.heading("#0", text="Имя", anchor=tk.W)
        self.structure_tree.heading("type", text="Тип", anchor=tk.W)
        self.structure_tree.heading("size", text="Размер", anchor=tk.E)
        
        # Вкладка "Предпросмотр разборки"
        preview_rebuild_frame = ttk.Frame(notebook)
        notebook.add(preview_rebuild_frame, text="Предпросмотр разборки")
        
        self.preview_rebuild_text = scrolledtext.ScrolledText(preview_rebuild_frame, wrap=tk.WORD, height=20, width=60)
        self.preview_rebuild_text.pack(fill=tk.BOTH, expand=True)
        self.preview_rebuild_text.config(state=tk.DISABLED)
        self.preview_rebuild_text.insert(tk.END, "Выберите файл проекта для предпросмотра структуры модулей...")
        
        # Вкладка "Предпросмотр сборки"
        preview_build_frame = ttk.Frame(notebook)
        notebook.add(preview_build_frame, text="Предпросмотр сборки")
        
        self.preview_build_text = scrolledtext.ScrolledText(preview_build_frame, wrap=tk.WORD, height=20, width=60)
        self.preview_build_text.pack(fill=tk.BOTH, expand=True)
        self.preview_build_text.config(state=tk.DISABLED)
        self.preview_build_text.insert(tk.END, "Выберите директорию с модулями для предпросмотра структуры файла...")
        
        # Вкладка "Информация"
        info_frame = ttk.Frame(notebook)
        notebook.add(info_frame, text="Информация")
        
        info_text = scrolledtext.ScrolledText(info_frame, wrap=tk.WORD, height=20, width=60)
        info_text.pack(fill=tk.BOTH, expand=True)
        info_text.insert(tk.END, f"{APP_NAME} v{APP_VERSION}\n\n")
        info_text.insert(tk.END, f"{APP_DESCRIPTION}\n\n")
        info_text.insert(tk.END, f"Автор: {APP_AUTHOR}\n")
        info_text.config(state=tk.DISABLED)
    
    def _create_status_bar(self):
        """Создание статусной строки"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        ttk.Label(status_frame, textvariable=self.status_text, relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(status_frame, text=f"v{APP_VERSION}", relief=tk.SUNKEN, anchor=tk.E, width=10).pack(side=tk.RIGHT)
    
    def _center_window(self):
        """Центрирование окна на экране"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def _load_settings(self) -> Optional[dict]:
        """Загрузка настроек из файла"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    if self.logger:
                        self.logger.debug(f"Настройки загружены из {self.settings_file}")
                    return settings
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Не удалось загрузить настройки: {e}")
            else:
                print(f"[WARNING] Не удалось загрузить настройки: {e}")
        return None
    
    def _save_settings(self):
        """Сохранение настроек в файл"""
        try:
            if not self.root:
                return
            
            # Получаем текущую геометрию окна
            geometry = self.root.geometry()
            # Парсим геометрию: "widthxheight+x+y" или "widthxheight"
            parts = geometry.split('+')
            size_part = parts[0]
            position = None
            
            if len(parts) > 1:
                position = {
                    'x': int(parts[1]),
                    'y': int(parts[2])
                }
            
            # Создаем словарь настроек
            settings = {
                'geometry': size_part,
                'position': position,
                'project_dir': self.project_dir.get() if self.project_dir else '',
                'main_file': self.main_file.get() if self.main_file else '',
                'output_dir': self.output_dir.get() if self.output_dir else ''
            }
            
            # Сохраняем в файл
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            if self.logger:
                self.logger.debug(f"Настройки сохранены в {self.settings_file}")
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Не удалось сохранить настройки: {e}")
            else:
                print(f"[WARNING] Не удалось сохранить настройки: {e}")
    
    def _on_closing(self):
        """Обработчик закрытия окна"""
        # Сохраняем настройки перед закрытием
        self._save_settings()
        if self.logger:
            self.logger.info("Приложение закрыто")
        self.root.destroy()
    
    def _save_settings_delayed(self):
        """Отложенное сохранение настроек (для автосохранения при изменении полей)"""
        if not self.root:
            return
        if hasattr(self, '_save_timer'):
            self.root.after_cancel(self._save_timer)
        self._save_timer = self.root.after(500, self._save_settings)  # Сохраняем через 500мс после последнего изменения
    
    def _on_window_configure(self, event):
        """Обработчик изменения размера и позиции окна"""
        # Сохраняем настройки только если это главное окно (не дочерние виджеты)
        if event.widget == self.root:
            # Используем after для отложенного сохранения (чтобы не сохранять при каждом движении мыши)
            self._save_settings_delayed()
    
    def _select_project(self):
        """Выбор директории проекта"""
        directory = filedialog.askdirectory(title="Выберите директорию проекта")
        if directory:
            self.project_dir.set(directory)
            self._log(f"Выбрана директория проекта: {directory}", "INFO")
            self._log(f"Абсолютный путь: {os.path.abspath(directory)}", "DEBUG")
            self._update_status(f"Проект: {os.path.basename(directory)}")
            # Загружаем структуру проекта
            self._load_project_structure(directory)
            # Обновляем предпросмотр разборки
            self._update_rebuild_preview()
    
    def _select_main_file(self):
        """Выбор главного файла проекта"""
        # Определяем начальную директорию для диалога
        initial_dir = self.project_dir.get() if self.project_dir.get() else os.path.expanduser("~")
        
        file_path = filedialog.askopenfilename(
            title="Выберите главный файл проекта",
            initialdir=initial_dir,
            filetypes=[("Python файлы", "*.py"), ("Все файлы", "*.*")]
        )
        
        if file_path:
            # Автоматически заполняем директорию проекта и имя файла
            file_dir = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            
            self.project_dir.set(file_dir)
            self.main_file.set(file_name)
            
            self._log(f"Выбран главный файл: {file_path}", "INFO")
            self._log(f"Директория проекта: {file_dir}", "INFO")
            self._log(f"Имя файла: {file_name}", "INFO")
            self._update_status(f"Файл: {file_name}")
            # Загружаем структуру проекта
            self._load_project_structure(file_dir)
            # Обновляем предпросмотр разборки
            self._update_rebuild_preview()
    
    def _select_output_dir(self):
        """Выбор выходной директории"""
        directory = filedialog.askdirectory(title="Выберите выходную директорию")
        if directory:
            self.output_dir.set(directory)
            self._log(f"Выбрана выходная директория: {directory}")
            # Обновляем предпросмотр разборки
            self._update_rebuild_preview()
            # Обновляем предпросмотр сборки
            self._update_build_preview()
    
    def _rebuild_project(self):
        """Разборка проекта на модули"""
        project_dir = self.project_dir.get()
        main_file = self.main_file.get()
        
        if not main_file:
            messagebox.showerror("Ошибка", "Укажите главный файл проекта")
            return
        
        # Определяем путь к главному файлу
        # Если указан полный путь к файлу, используем его
        if os.path.isabs(main_file) and os.path.exists(main_file):
            main_file_path = main_file
            project_dir = os.path.dirname(main_file_path)
        elif project_dir:
            # Если указана директория проекта, объединяем с именем файла
            main_file_path = os.path.join(project_dir, main_file)
        else:
            # Пытаемся найти файл относительно текущей директории
            if os.path.exists(main_file):
                main_file_path = os.path.abspath(main_file)
                project_dir = os.path.dirname(main_file_path)
            else:
                messagebox.showerror("Ошибка", f"Файл не найден: {main_file}\nВыберите файл через кнопку '...' или укажите директорию проекта")
                return
        
        if not os.path.exists(main_file_path):
            messagebox.showerror("Ошибка", f"Файл не найден: {main_file_path}")
            return
        
        if project_dir and not os.path.exists(project_dir):
            messagebox.showerror("Ошибка", f"Директория не найдена: {project_dir}")
            return
        
        output_dir = self.output_dir.get() or os.path.join(project_dir, "modules")
        
        self._log(f"Начало разборки проекта: {project_dir}")
        self._log(f"Главный файл: {main_file}")
        self._log(f"Выходная директория: {output_dir}")
        self._update_status("Разборка проекта...")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self._run_rebuild, args=(main_file_path, output_dir))
        thread.daemon = True
        thread.start()
    
    def _build_project(self):
        """Сборка модулей в один файл"""
        modules_dir = self.output_dir.get() or os.path.join(self.project_dir.get(), "modules")
        
        if not modules_dir:
            messagebox.showerror("Ошибка", "Укажите директорию с модулями")
            return
        
        # Преобразуем в абсолютный путь
        modules_dir = os.path.abspath(modules_dir)
        
        if not os.path.exists(modules_dir):
            error_msg = f"Директория не найдена: {modules_dir}"
            self._log(f"[ERROR] {error_msg}", "ERROR")
            messagebox.showerror("Ошибка", error_msg)
            return
        
        # Определяем выходной файл - создаем ВНУТРИ выбранной директории
        # Используем имя из main_file или имя проекта, а не имя папки с модулями
        project_name = os.path.basename(self.project_dir.get()) if self.project_dir.get() else os.path.basename(modules_dir)
        main_file_name = os.path.splitext(self.main_file.get())[0] if self.main_file.get() else project_name
        # Создаем файл ВНУТРИ директории с модулями
        output_file = os.path.join(modules_dir, f"{main_file_name}_built.py")
        output_file = os.path.abspath(output_file)
        
        self._log(f"Начало сборки модулей: {modules_dir}", "INFO")
        self._log(f"Выходной файл: {output_file}", "INFO")
        self._log(f"Директория выходного файла: {os.path.dirname(output_file)}", "DEBUG")
        self._update_status("Сборка модулей...")
        
        # Обновляем предпросмотр сборки
        self._update_build_preview()
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self._run_build, args=(modules_dir, output_file))
        thread.daemon = True
        thread.start()
    
    def _create_distribution(self):
        """Создание дистрибутива"""
        project_dir = self.project_dir.get()
        main_file = self.main_file.get()
        
        if not project_dir:
            messagebox.showerror("Ошибка", "Выберите директорию проекта")
            return
        
        self._log(f"Создание дистрибутива для проекта: {project_dir}")
        self._update_status("Создание дистрибутива...")
        
        messagebox.showinfo("Информация", "Функция создания дистрибутива будет реализована в ближайшее время")
        self._update_status("Готов к работе")
    
    def _run_rebuild(self, source_file: str, output_dir: str):
        """Выполнение разборки в отдельном потоке"""
        try:
            from core.rebuilder import rebuild_file
            
            success = rebuild_file(source_file, output_dir)
            
            if success:
                self._log("[SUCCESS] Разборка завершена успешно!")
                self._update_status("Разборка завершена успешно")
                messagebox.showinfo("Успех", f"Разборка завершена успешно!\nМодули созданы в: {output_dir}")
            else:
                self._log("[ERROR] Разборка завершена с ошибками")
                self._update_status("Ошибка разборки")
                messagebox.showerror("Ошибка", "Разборка завершена с ошибками. Проверьте логи.")
        except Exception as e:
            self._log(f"[ERROR] Ошибка: {e}")
            self._update_status("Ошибка")
            messagebox.showerror("Ошибка", f"Ошибка при разборке: {e}")
    
    def _run_build(self, modules_dir: str, output_file: str):
        """Выполнение сборки в отдельном потоке"""
        try:
            self._log(f"[BUILD] Начало сборки модулей", "DEBUG")
            self._log(f"[BUILD] Директория модулей: {modules_dir}", "DEBUG")
            self._log(f"[BUILD] Выходной файл: {output_file}", "DEBUG")
            
            # Проверяем существование директории модулей
            if not os.path.exists(modules_dir):
                error_msg = f"Директория модулей не найдена: {modules_dir}"
                self._log(f"[ERROR] {error_msg}", "ERROR")
                self._update_status("Ошибка: директория не найдена")
                messagebox.showerror("Ошибка", error_msg)
                return
            
            # Проверяем абсолютный путь
            output_file_abs = os.path.abspath(output_file)
            self._log(f"[BUILD] Абсолютный путь к выходному файлу: {output_file_abs}", "DEBUG")
            
            from core.builder import build_modules
            
            success = build_modules(modules_dir, output_file_abs)
            
            if success:
                # Проверяем, что файл действительно создан
                time.sleep(0.2)  # Небольшая задержка для синхронизации файловой системы
                
                # Проверяем несколько раз
                file_exists = False
                for i in range(5):
                    if os.path.exists(output_file_abs):
                        file_exists = True
                        break
                    time.sleep(0.1)
                
                if file_exists:
                    file_size = os.path.getsize(output_file_abs)
                    output_dir = os.path.dirname(output_file_abs)
                    
                    self._log(f"[SUCCESS] Сборка завершена успешно!", "INFO")
                    self._log(f"[SUCCESS] Файл создан: {output_file_abs}", "INFO")
                    self._log(f"[SUCCESS] Размер файла: {file_size} байт", "INFO")
                    self._log(f"[SUCCESS] Директория: {output_dir}", "INFO")
                    self._log(f"[SUCCESS] Файл существует: {os.path.exists(output_file_abs)}", "DEBUG")
                    
                    # Проверяем содержимое директории
                    if os.path.exists(output_dir):
                        files_in_dir = os.listdir(output_dir)
                        self._log(f"[DEBUG] Файлы в директории: {files_in_dir}", "DEBUG")
                        if os.path.basename(output_file_abs) in files_in_dir:
                            self._log(f"[SUCCESS] Файл найден в директории!", "INFO")
                        else:
                            self._log(f"[WARNING] Файл не найден в списке файлов директории!", "WARNING")
                            self._log(f"[WARNING] Ищем: {os.path.basename(output_file_abs)}", "WARNING")
                            self._log(f"[WARNING] В директории: {files_in_dir}", "WARNING")
                    
                    self._update_status("Сборка завершена успешно")
                    messagebox.showinfo("Успех", f"Сборка завершена успешно!\nФайл создан: {output_file_abs}\nРазмер: {file_size} байт")
                else:
                    output_dir = os.path.dirname(output_file_abs)
                    error_msg = f"Файл не найден после сборки: {output_file_abs}"
                    self._log(f"[ERROR] {error_msg}", "ERROR")
                    self._log(f"[ERROR] Директория существует: {os.path.exists(output_dir)}", "ERROR")
                    if os.path.exists(output_dir):
                        files_in_dir = os.listdir(output_dir)
                        self._log(f"[ERROR] Файлы в директории: {files_in_dir}", "ERROR")
                    else:
                        self._log(f"[ERROR] Директория не существует: {output_dir}", "ERROR")
                    self._update_status("Ошибка: файл не создан")
                    messagebox.showerror("Ошибка", error_msg + f"\nДиректория: {output_dir}\nПроверьте логи в папке Logs/")
            else:
                error_msg = "Сборка завершена с ошибками"
                self._log(f"[ERROR] {error_msg}", "ERROR")
                self._update_status("Ошибка сборки")
                messagebox.showerror("Ошибка", error_msg + "\nПроверьте логи в папке Logs/")
        except Exception as e:
            import traceback
            error_msg = f"Ошибка при сборке: {e}"
            self._log(f"[ERROR] {error_msg}", "ERROR")
            self._log(f"[ERROR] Traceback: {traceback.format_exc()}", "ERROR")
            self._update_status("Ошибка")
            messagebox.showerror("Ошибка", error_msg + "\nПроверьте логи в папке Logs/")
    
    def _log(self, message: str, level: str = "INFO"):
        """Добавление сообщения в лог"""
        # Логируем в GUI
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
        
        # Логируем в файл
        if self.logger:
            if level == "ERROR":
                self.logger.error(message)
            elif level == "WARNING":
                self.logger.warning(message)
            elif level == "DEBUG":
                self.logger.debug(message)
            else:
                self.logger.info(message)
    
    def _update_status(self, status: str):
        """Обновление статусной строки"""
        self.status_text.set(status)
        self.root.update_idletasks()
    
    def _show_about(self):
        """Показ окна 'О программе'"""
        about_text = f"""{APP_NAME}

Версия: {APP_VERSION}

{APP_DESCRIPTION}

Автор: {APP_AUTHOR}
Компания: ООО "НПА Вира-Реалтайм"

© 2025 Все права защищены"""
        
        messagebox.showinfo("О программе", about_text)
    
    def _show_docs(self):
        """Показ документации"""
        docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
        if os.path.exists(docs_path):
            messagebox.showinfo("Документация", f"Документация находится в: {docs_path}")
        else:
            messagebox.showinfo("Документация", "Документация будет добавлена в ближайшее время")
    
    def _load_project_structure(self, project_dir: str):
        """Загрузка и отображение структуры проекта"""
        try:
            # Очищаем дерево
            for item in self.structure_tree.get_children():
                self.structure_tree.delete(item)
            
            if not os.path.exists(project_dir):
                return
            
            # Добавляем корневой элемент
            root_item = self.structure_tree.insert("", "end", text=os.path.basename(project_dir), 
                                                   values=("Директория", ""))
            
            # Рекурсивно добавляем файлы и папки
            self._add_directory_to_tree(root_item, project_dir, project_dir)
            
            # Разворачиваем корневой элемент
            self.structure_tree.item(root_item, open=True)
            
            self._log(f"Структура проекта загружена: {project_dir}")
            
        except Exception as e:
            self._log(f"[ERROR] Ошибка загрузки структуры: {e}")
    
    def _add_directory_to_tree(self, parent_item, dir_path: str, root_path: str):
        """Рекурсивное добавление директории в дерево"""
        try:
            items = []
            dirs = []
            
            # Собираем файлы и директории
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                
                # Пропускаем скрытые файлы и служебные директории
                if item.startswith('.') or item in ['__pycache__', '.git', '.metadata']:
                    continue
                
                if os.path.isdir(item_path):
                    dirs.append((item, item_path))
                else:
                    items.append((item, item_path))
            
            # Сначала добавляем директории
            for name, path in sorted(dirs):
                rel_path = os.path.relpath(path, root_path)
                size = self._get_directory_size(path)
                dir_item = self.structure_tree.insert(parent_item, "end", text=name,
                                                     values=("Директория", self._format_size(size)),
                                                     tags=("directory",))
                # Рекурсивно добавляем содержимое
                self._add_directory_to_tree(dir_item, path, root_path)
            
            # Затем добавляем файлы
            for name, path in sorted(items):
                rel_path = os.path.relpath(path, root_path)
                file_size = os.path.getsize(path)
                file_type = self._get_file_type(name)
                self.structure_tree.insert(parent_item, "end", text=name,
                                          values=(file_type, self._format_size(file_size)),
                                          tags=("file",))
        
        except PermissionError:
            pass
        except Exception as e:
            self._log(f"[WARNING] Ошибка при добавлении {dir_path}: {e}")
    
    def _get_directory_size(self, dir_path: str) -> int:
        """Получение размера директории"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(dir_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        pass
        except Exception:
            pass
        return total_size
    
    def _get_file_type(self, filename: str) -> str:
        """Определение типа файла"""
        ext = os.path.splitext(filename)[1].lower()
        type_map = {
            '.py': 'Python',
            '.pyc': 'Python (compiled)',
            '.md': 'Markdown',
            '.txt': 'Text',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.xml': 'XML',
            '.html': 'HTML',
            '.css': 'CSS',
            '.js': 'JavaScript',
            '.png': 'Image',
            '.jpg': 'Image',
            '.jpeg': 'Image',
            '.gif': 'Image',
            '.ico': 'Icon',
        }
        return type_map.get(ext, 'File')
    
    def _format_size(self, size: int) -> str:
        """Форматирование размера файла"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def _update_rebuild_preview(self):
        """Обновление предпросмотра разборки"""
        try:
            if not self.preview_rebuild_text:
                return
            
            self.preview_rebuild_text.config(state=tk.NORMAL)
            self.preview_rebuild_text.delete(1.0, tk.END)
            
            # Получаем параметры
            project_dir = self.project_dir.get()
            main_file = self.main_file.get()
            output_dir = self.output_dir.get()
            
            if not main_file:
                self.preview_rebuild_text.insert(tk.END, "Выберите файл проекта для предпросмотра структуры модулей...")
                self.preview_rebuild_text.config(state=tk.DISABLED)
                return
            
            # Определяем путь к файлу
            if os.path.isabs(main_file) and os.path.exists(main_file):
                main_file_path = main_file
            elif project_dir:
                main_file_path = os.path.join(project_dir, main_file)
            else:
                if os.path.exists(main_file):
                    main_file_path = os.path.abspath(main_file)
                else:
                    self.preview_rebuild_text.insert(tk.END, f"Файл не найден: {main_file}")
                    self.preview_rebuild_text.config(state=tk.DISABLED)
                    return
            
            if not os.path.exists(main_file_path):
                self.preview_rebuild_text.insert(tk.END, f"Файл не найден: {main_file_path}")
                self.preview_rebuild_text.config(state=tk.DISABLED)
                return
            
            # Парсим файл для получения структуры
            from core.parser import CodeParser
            
            parser = CodeParser(main_file_path)
            if not parser.parse():
                self.preview_rebuild_text.insert(tk.END, f"Ошибка парсинга файла: {main_file_path}")
                self.preview_rebuild_text.config(state=tk.DISABLED)
                return
            
            structure = parser.get_structure()
            
            # Определяем выходную директорию
            if not output_dir:
                if project_dir:
                    output_dir = os.path.join(project_dir, "modules")
                else:
                    output_dir = os.path.join(os.path.dirname(main_file_path), "modules")
            
            # Генерируем предпросмотр
            preview = []
            preview.append("=" * 70)
            preview.append("ПРЕДПРОСМОТР РАЗБОРКИ НА МОДУЛИ")
            preview.append("=" * 70)
            preview.append("")
            preview.append(f"Исходный файл: {main_file_path}")
            preview.append(f"Выходная директория: {output_dir}")
            preview.append("")
            preview.append("-" * 70)
            preview.append("СТРУКТУРА МОДУЛЕЙ:")
            preview.append("-" * 70)
            preview.append("")
            
            # Импорты
            if structure['imports']:
                preview.append("📁 imports.py")
                preview.append(f"   Импорты: {len(structure['imports'])}")
                for imp in structure['imports'][:5]:
                    preview.append(f"   - {imp.get('name', 'N/A')}")
                if len(structure['imports']) > 5:
                    preview.append(f"   ... и еще {len(structure['imports']) - 5}")
                preview.append("")
            
            # Константы
            if structure['constants']:
                preview.append("📁 config.py")
                preview.append(f"   Константы: {len(structure['constants'])}")
                for const in structure['constants'][:5]:
                    preview.append(f"   - {const.get('name', 'N/A')}")
                if len(structure['constants']) > 5:
                    preview.append(f"   ... и еще {len(structure['constants']) - 5}")
                preview.append("")
            
            # Классы
            if structure['classes']:
                preview.append("📁 core/")
                for cls in structure['classes']:
                    preview.append(f"   📄 {cls.get('name', 'N/A')}.py")
                    preview.append(f"      Методы: {len(cls.get('methods', []))}")
                    if cls.get('docstring'):
                        doc = cls['docstring'].split('\n')[0][:50]
                        preview.append(f"      Описание: {doc}...")
                preview.append("")
            
            # Функции
            if structure['functions']:
                preview.append("📁 utils/")
                for func in structure['functions'][:10]:
                    preview.append(f"   📄 {func.get('name', 'N/A')}.py")
                    if func.get('docstring'):
                        doc = func['docstring'].split('\n')[0][:50]
                        preview.append(f"      Описание: {doc}...")
                if len(structure['functions']) > 10:
                    preview.append(f"   ... и еще {len(structure['functions']) - 10} функций")
                preview.append("")
            
            preview.append("-" * 70)
            preview.append("СТАТИСТИКА:")
            preview.append("-" * 70)
            preview.append(f"Всего строк: {structure.get('total_lines', 0)}")
            preview.append(f"Импортов: {len(structure.get('imports', []))}")
            preview.append(f"Констант: {len(structure.get('constants', []))}")
            preview.append(f"Классов: {len(structure.get('classes', []))}")
            preview.append(f"Функций: {len(structure.get('functions', []))}")
            preview.append("")
            preview.append("=" * 70)
            
            self.preview_rebuild_text.insert(tk.END, '\n'.join(preview))
            self.preview_rebuild_text.config(state=tk.DISABLED)
            
        except Exception as e:
            if self.preview_rebuild_text:
                self.preview_rebuild_text.config(state=tk.NORMAL)
                self.preview_rebuild_text.delete(1.0, tk.END)
                self.preview_rebuild_text.insert(tk.END, f"Ошибка генерации предпросмотра: {e}")
                self.preview_rebuild_text.config(state=tk.DISABLED)
    
    def _update_build_preview(self):
        """Обновление предпросмотра сборки"""
        try:
            if not self.preview_build_text:
                return
            
            self.preview_build_text.config(state=tk.NORMAL)
            self.preview_build_text.delete(1.0, tk.END)
            
            # Получаем параметры
            modules_dir = self.output_dir.get() or os.path.join(self.project_dir.get() or "", "modules")
            
            if not modules_dir or not os.path.exists(modules_dir):
                self.preview_build_text.insert(tk.END, "Выберите директорию с модулями для предпросмотра структуры файла...")
                self.preview_build_text.config(state=tk.DISABLED)
                return
            
            modules_dir = os.path.abspath(modules_dir)
            
            # Определяем выходной файл
            project_name = os.path.basename(self.project_dir.get()) if self.project_dir.get() else os.path.basename(modules_dir)
            main_file_name = os.path.splitext(self.main_file.get())[0] if self.main_file.get() else project_name
            output_file = os.path.join(modules_dir, f"{main_file_name}_built.py")
            
            # Сканируем модули
            modules = []
            for root, dirs, files in os.walk(modules_dir):
                # Пропускаем метаданные и __pycache__
                if 'metadata' in root or '__pycache__' in root:
                    continue
                
                for file in files:
                    if file.endswith('.py') and file != '__init__.py':
                        module_path = os.path.join(root, file)
                        rel_path = os.path.relpath(module_path, modules_dir)
                        modules.append(rel_path)
            
            # Генерируем предпросмотр
            preview = []
            preview.append("=" * 70)
            preview.append("ПРЕДПРОСМОТР СБОРКИ МОДУЛЕЙ")
            preview.append("=" * 70)
            preview.append("")
            preview.append(f"Директория модулей: {modules_dir}")
            preview.append(f"Выходной файл: {output_file}")
            preview.append("")
            preview.append("-" * 70)
            preview.append("СТРУКТУРА ФАЙЛА:")
            preview.append("-" * 70)
            preview.append("")
            
            if not modules:
                preview.append("⚠️  Модули не найдены в директории")
                preview.append("")
                preview.append("Проверьте, что директория содержит .py файлы (кроме __init__.py)")
            else:
                # Сортируем модули по приоритету
                priority_files = ['config.py', 'imports.py']
                other_modules = [m for m in modules if m not in priority_files]
                
                preview.append("📄 Заголовок файла")
                preview.append("")
                
                # Импорты
                preview.append("📦 Импорты")
                for module in modules:
                    if 'imports' in module.lower() or module == 'imports.py':
                        preview.append(f"   - {module}")
                preview.append("")
                
                # Конфигурация
                preview.append("⚙️  Конфигурация")
                for module in modules:
                    if 'config' in module.lower() or module == 'config.py':
                        preview.append(f"   - {module}")
                preview.append("")
                
                # Модули по категориям
                categories = {}
                for module in other_modules:
                    category = module.split('/')[0] if '/' in module else 'root'
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(module)
                
                for category in sorted(categories.keys()):
                    preview.append(f"📁 {category}/")
                    for module in sorted(categories[category])[:10]:
                        preview.append(f"   - {module}")
                    if len(categories[category]) > 10:
                        preview.append(f"   ... и еще {len(categories[category]) - 10} модулей")
                    preview.append("")
            
            preview.append("-" * 70)
            preview.append("СТАТИСТИКА:")
            preview.append("-" * 70)
            preview.append(f"Всего модулей: {len(modules)}")
            preview.append(f"Приоритетных: {len([m for m in modules if m in priority_files])}")
            preview.append(f"Остальных: {len([m for m in modules if m not in priority_files])}")
            preview.append("")
            preview.append("=" * 70)
            
            self.preview_build_text.insert(tk.END, '\n'.join(preview))
            self.preview_build_text.config(state=tk.DISABLED)
            
        except Exception as e:
            if self.preview_build_text:
                self.preview_build_text.config(state=tk.NORMAL)
                self.preview_build_text.delete(1.0, tk.END)
                self.preview_build_text.insert(tk.END, f"Ошибка генерации предпросмотра: {e}")
                self.preview_build_text.config(state=tk.DISABLED)
    
    def run(self):
        """Запуск главного цикла"""
        if self.root:
            self._log(f"Запуск {APP_NAME} v{APP_VERSION}")
            self._log("Готов к работе")
            
            # Если есть текущая директория, загружаем её структуру
            if self.project_dir and self.project_dir.get():
                self._load_project_structure(self.project_dir.get())
            
            self.root.mainloop()

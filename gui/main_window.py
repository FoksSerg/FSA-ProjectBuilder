#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Главное окно GUI
Версия: 0.1.0
"""

from __future__ import print_function
import sys
import os

class MainWindow:
    """Главное окно приложения"""
    
    def __init__(self):
        """Инициализация главного окна"""
        self.root = None
        self._init_gui()
    
    def _init_gui(self):
        """Инициализация GUI"""
        try:
            import tkinter as tk
            from tkinter import ttk
            
            self.root = tk.Tk()
            self.root.title("FSA-ProjectBuilder")
            self.root.geometry("800x600")
            
            # Создаем базовый интерфейс
            label = tk.Label(
                self.root,
                text="FSA-ProjectBuilder\nGUI интерфейс будет реализован в ближайшее время",
                font=("Arial", 14),
                justify="center"
            )
            label.pack(expand=True)
            
        except ImportError:
            print("[ERROR] tkinter не найден. Установите python3-tk")
            sys.exit(1)
    
    def run(self):
        """Запуск главного цикла"""
        if self.root:
            self.root.mainloop()


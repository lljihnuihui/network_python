"""Точка входа для тестов.

test_errors.py импортирует приложение как `from solution import app`.
Исправленное приложение реализовано в task.py — здесь только реэкспорт.

task.py грузим по абсолютному пути под уникальным именем модуля: у соседнего
задания (01_bookstore) тоже есть task.py, и обычный `from task import app`
подхватил бы уже закэшированный чужой модуль.
"""

import importlib.util
import os

_TASK_PATH = os.path.join(os.path.dirname(__file__), "task.py")
_spec = importlib.util.spec_from_file_location("errors_task", _TASK_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

app = _module.app

__all__ = ["app"]

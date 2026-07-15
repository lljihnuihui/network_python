"""
02_errors_and_tests — чиним и тестируем 🛠️

В app.py лежит сломанное FastAPI-приложение. Найдите и исправьте ВСЕ проблемы.

Найденные проблемы в app.py и как они исправлены здесь:
    1. GET /items/{id}   — ITEMS[item_id] падал с IndexError (500) вместо 404.
    2. POST /items       — возвращал 200 вместо 201.
    3. PUT /items/{id}   — при отсутствии отдавал 200 c {"error": ...} вместо 404;
                           ItemUpdate требовал обязательное unknown_field.
    4. DELETE /items/{id} — возвращал 200 {"deleted": True} вместо 204;
                           .pop(index) съезжал по id (list вместо dict).
    5. GET /divide       — деление на ноль → 500 вместо 400.
    6. GET /slow-sync    — sync time.sleep блокировал event loop.
    7. get_counter       — глобальный счётчик без синхронизации (race condition).
    8. Хранилище list с item_id как индекс → id съезжали после delete.
       Заменено на dict[int, dict] с монотонным NEXT_ID.

Задача Б: тесты — в test_errors.py (импортируют app из solution.py).
"""

import asyncio
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

ITEMS: dict[int, dict] = {}
NEXT_ID = 1
COUNTER = 0
_counter_lock = threading.Lock()


class ItemCreate(BaseModel):
    name: str


class ItemUpdate(BaseModel):
    name: str = ""


# ═══════════════════════════════════════════════════════════
# ИСПРАВЛЕННЫЕ ЭНДПОИНТЫ
# ═══════════════════════════════════════════════════════════


@app.get("/items")
def list_items():
    return {"items": list(ITEMS.values())}


@app.get("/items/{item_id}")
def get_item(item_id: int):
    item = ITEMS.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.post("/items", status_code=201)
def create_item(item: ItemCreate):
    global NEXT_ID
    new_id = NEXT_ID
    NEXT_ID += 1
    ITEMS[new_id] = {"id": new_id, "name": item.name}
    return {"id": new_id}


@app.get("/items/{item_id}/counter")
def get_counter(item_id: int):
    # Синхронизируем инкремент, чтобы не было race condition.
    global COUNTER
    with _counter_lock:
        COUNTER += 1
        current = COUNTER
    return {"counter": current}


@app.put("/items/{item_id}")
def update_item(item_id: int, update: ItemUpdate):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    ITEMS[item_id] = {"id": item_id, "name": update.name}
    return ITEMS[item_id]


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    del ITEMS[item_id]
    return None


@app.get("/divide")
def divide(a: int, b: int):
    if b == 0:
        raise HTTPException(status_code=400, detail="Division by zero")
    return {"result": a / b}


@app.get("/slow-sync")
async def slow_sync():
    # async + await asyncio.sleep — не блокирует event loop.
    await asyncio.sleep(0.5)
    return {"status": "done"}

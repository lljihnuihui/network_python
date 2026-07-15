"""
01_bookstore — CRUD API для книжного магазина 📚

Спроектируйте REST API для управления каталогом книг.

Спецификация эндпоинтов (ничего не менять — тесты завязаны на них):

    GET    /books              — список книг (с опциональной фильтрацией)
    GET    /books/{id}         — одна книга по id
    POST   /books              — создать книгу
    PUT    /books/{id}         — полностью обновить книгу
    DELETE /books/{id}         — удалить книгу
    GET    /books/search       — поиск книг по названию или автору

    # Дополнительно — категории
    GET    /categories         — список категорий
    POST   /categories         — создать категорию

Требования к реализации:
    1. Используйте FastAPI + Pydantic
    2. Храните данные в памяти (глобальный список/словарь)
    3. Правильные HTTP-статусы:
        - 200 — успешный GET, PUT
        - 201 — успешный POST
        - 204 — успешный DELETE
        - 404 — ресурс не найден
        - 409 — конфликт (например, дубликат)
        - 422 — невалидные данные (Pydantic сам это делает)
    4. Валидация полей через Pydantic Field:
        - title:  не пустой, до 100 символов
        - author: не пустой, до 100 символов
        - year:   ≥ 0, до 2025
        - isbn:   строка 10 или 13 цифр (978-5-xxx...)
        - price:  > 0
        - category_id: опционально, ссылка на категорию
    5. Кастомная обработка ошибок:
        - BookNotFoundException → 404 c {"detail": "Book not found", "code": "NOT_FOUND"}
        - DuplicateIsbnException → 409 c {"detail": "...", "code": "DUPLICATE_ISBN"}
    6. Поиск /books/search?query=... — ищет по title и author (case-insensitive)
    7. Фильтрация GET /books?category_id=N&year=2024
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional

# ═══════════════════════════════════════════════════════════
# МОДЕЛИ
# ═══════════════════════════════════════════════════════════


class Category(BaseModel):
    """Доменная модель категории. Возвращается в ответах."""

    id: int
    name: str = Field(min_length=1, max_length=50)


class CategoryCreate(BaseModel):
    """Модель для создания категории (без id, лишние поля запрещены)."""

    name: str = Field(min_length=1, max_length=50)

    model_config = {"extra": "forbid"}


class Book(BaseModel):
    """Доменная модель книги. Возвращается в ответах GET/PUT."""

    id: int
    title: str = Field(min_length=1, max_length=100)
    author: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=0, le=2025)
    isbn: str
    price: float = Field(gt=0)
    category_id: Optional[int] = None


class BookCreate(BaseModel):
    """Модель для создания/обновления книги (без id — сервер сгенерирует)."""

    title: str = Field(min_length=1, max_length=100)
    author: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=0, le=2025)
    isbn: str
    price: float = Field(gt=0)
    category_id: Optional[int] = None

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, v: str) -> str:
        """ISBN — 10 или 13 цифр (дефисы разрешены как разделители)."""
        digits = v.replace("-", "").replace(" ", "")
        if not digits.isdigit() or len(digits) not in (10, 13):
            raise ValueError("ISBN должен содержать 10 или 13 цифр")
        return v


# ═══════════════════════════════════════════════════════════
# ИСКЛЮЧЕНИЯ
# ═══════════════════════════════════════════════════════════


class BookNotFoundException(Exception):
    """404 — книга не найдена."""

    def __init__(self, book_id: Optional[int] = None):
        self.book_id = book_id
        super().__init__("Book not found")


class DuplicateIsbnException(Exception):
    """409 — ISBN уже существует."""

    def __init__(self, isbn: str):
        self.isbn = isbn
        super().__init__(f"Book with isbn {isbn} already exists")


# ═══════════════════════════════════════════════════════════
# ПРИЛОЖЕНИЕ
# ═══════════════════════════════════════════════════════════

app = FastAPI(title="Bookstore API")

# Хранилище
BOOKS: list[dict] = []
CATEGORIES: list[dict] = []

_next_book_id = 1
_next_category_id = 1


# ═══════════════════════════════════════════════════════════
# ОБРАБОТЧИКИ ОШИБОК (плоское тело {"detail": ..., "code": ...})
# ═══════════════════════════════════════════════════════════


@app.exception_handler(BookNotFoundException)
def book_not_found_handler(request: Request, exc: BookNotFoundException):
    return JSONResponse(
        status_code=404,
        content={"detail": "Book not found", "code": "NOT_FOUND"},
    )


@app.exception_handler(DuplicateIsbnException)
def duplicate_isbn_handler(request: Request, exc: DuplicateIsbnException):
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc), "code": "DUPLICATE_ISBN"},
    )


# ═══════════════════════════════════════════════════════════
# КАТЕГОРИИ
# ═══════════════════════════════════════════════════════════


@app.get("/categories")
def list_categories():
    """GET /categories — список всех категорий."""
    return CATEGORIES


@app.post("/categories", status_code=201)
def create_category(category: CategoryCreate):
    """POST /categories — создать категорию."""
    global _next_category_id
    new = {"id": _next_category_id, "name": category.name}
    _next_category_id += 1
    CATEGORIES.append(new)
    return new


# ═══════════════════════════════════════════════════════════
# CRUD КНИГ
# ═══════════════════════════════════════════════════════════


@app.get("/books")
def list_books(category_id: Optional[int] = None, year: Optional[int] = None):
    """GET /books — список книг. Опциональная фильтрация по category_id и year."""
    result = BOOKS
    if category_id is not None:
        result = [b for b in result if b["category_id"] == category_id]
    if year is not None:
        result = [b for b in result if b["year"] == year]
    return result


@app.get("/books/search")
def search_books(query: str):
    """GET /books/search?query=... — поиск по title и author (case-insensitive)."""
    q = query.lower()
    return [
        b for b in BOOKS if q in b["title"].lower() or q in b["author"].lower()
    ]


@app.get("/books/{book_id}")
def get_book(book_id: int):
    """GET /books/{id} — одна книга."""
    book = _find_book(book_id)
    if book is None:
        raise BookNotFoundException(book_id)
    return book


@app.post("/books", status_code=201)
def create_book(book: BookCreate):
    """POST /books — создать книгу.

    Проверять уникальность ISBN. Если дубликат — DuplicateIsbnException.
    """
    global _next_book_id
    if any(b["isbn"] == book.isbn for b in BOOKS):
        raise DuplicateIsbnException(book.isbn)
    new = {"id": _next_book_id, **book.model_dump()}
    _next_book_id += 1
    BOOKS.append(new)
    return new


@app.put("/books/{book_id}")
def update_book(book_id: int, book: BookCreate):
    """PUT /books/{id} — полностью обновить книгу."""
    existing = _find_book(book_id)
    if existing is None:
        raise BookNotFoundException(book_id)
    # ISBN может смениться — проверяем, что новый не занят другой книгой
    if any(b["isbn"] == book.isbn and b["id"] != book_id for b in BOOKS):
        raise DuplicateIsbnException(book.isbn)
    existing.update(book.model_dump())
    existing["id"] = book_id
    return existing


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    """DELETE /books/{id} — удалить книгу."""
    book = _find_book(book_id)
    if book is None:
        raise BookNotFoundException(book_id)
    BOOKS.remove(book)
    return None


# ═══════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════


def _find_book(book_id: int) -> Optional[dict]:
    """Найти книгу по id или вернуть None."""
    return next((b for b in BOOKS if b["id"] == book_id), None)

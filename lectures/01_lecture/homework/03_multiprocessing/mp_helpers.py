def is_prime(n: int) -> bool:
    """Проверка числа на простоту (CPU-bound)."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def heavy_compute(x: int) -> int:
    """'Тяжёлая' функция: сумма простых чисел до x."""
    total = 0
    for n in range(2, x + 1):
        if is_prime(n):
            total += n
    return total

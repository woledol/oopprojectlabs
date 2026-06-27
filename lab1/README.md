# Лабораторная работа 1

Система управления заявками в библиотеке.

## Запуск проверок

```bash
cd lab1
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m ruff check .
.venv/bin/python -m coverage run -m pytest
.venv/bin/python -m coverage report
```

Порог покрытия задан в `pyproject.toml`: не меньше 70%.

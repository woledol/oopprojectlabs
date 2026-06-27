# Лабораторная работа 2

Бэкенд-система управления арендой автомобилей.

## Что внутри

- REST API на FastAPI.
- Отдельные слои: модели, хранилище, сервисы, контроллеры.
- Проверки ролей: CLIENT, MANAGER, ADMIN.
- Уникальные VIN и username.
- Проверка возраста, водительского стажа и доступности автомобиля.
- Автоматическое подтверждение заявки для пользователя с ролями CLIENT и MANAGER.
- Расчет стоимости договора и штрафов при возврате.
- Тесты с покрытием не ниже 70%.
- Проверка кода через Ruff.

## Запуск

```bash
cd lab2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
ruff check .
uvicorn rental_service.main:app --reload
```

## Тестовые пользователи

При старте приложение создает пользователей:

| id | username | роли |
| --- | --- | --- |
| 1 | admin | ADMIN |
| 2 | manager | MANAGER |
| 3 | client | CLIENT |
| 4 | client_manager | CLIENT, MANAGER |

Для защищенных ручек передавай заголовок:

```http
X-User-Id: 1
```

## Основные ручки

- `GET /cars` — каталог доступных автомобилей с фильтрами.
- `POST /cars` — добавить автомобиль, только MANAGER или ADMIN.
- `PATCH /cars/{car_id}/status` — изменить статус автомобиля.
- `POST /rentals` — создать заявку на аренду.
- `PATCH /rentals/{rental_id}/approve` — одобрить заявку.
- `PATCH /rentals/{rental_id}/reject` — отклонить заявку.
- `PATCH /rentals/{rental_id}/complete` — завершить аренду и начислить штрафы.
- `POST /users` — добавить пользователя, только ADMIN.
- `PATCH /users/{user_id}/roles` — изменить роли пользователя, только ADMIN.

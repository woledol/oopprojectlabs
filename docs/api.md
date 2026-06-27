# Договоры запросов

## user_service

Базовый адрес: `http://localhost:8000`

### `POST /api/register`

Запрос:

```json
{
  "fullName": "Иван Иванов",
  "username": "ivan",
  "password": "secret123"
}
```

Ответ `201`:

```json
{
  "token": "session-token",
  "user": {
    "id": "uuid",
    "username": "ivan",
    "fullName": "Иван Иванов",
    "createdAt": "2026-06-27T10:00:00+00:00"
  }
}
```

Ошибки: `400`, `409`.

### `POST /api/login`

Запрос:

```json
{
  "username": "ivan",
  "password": "secret123"
}
```

Ответ `200`: такой же, как у регистрации.

Ошибки: `401`.

### `GET /api/me`

Заголовок:

```text
Authorization: Bearer session-token
```

Ответ `200`:

```json
{
  "id": "uuid",
  "username": "ivan",
  "fullName": "Иван Иванов",
  "createdAt": "2026-06-27T10:00:00+00:00"
}
```

Ошибки: `401`.

### `POST /api/predict`

Заголовок:

```text
Authorization: Bearer session-token
```

Запрос:

```json
{
  "patronymic": "Сергеевна"
}
```

Ответ `200`:

```json
{
  "patronymic": "Сергеевна",
  "gender": "female",
  "bestName": "Сергей",
  "confidence": 0.98,
  "candidates": [
    {
      "name": "Сергей",
      "confidence": 0.98,
      "reason": "Найдено точное соответствие в словаре распространенных отчеств."
    }
  ],
  "historyItem": {
    "id": "uuid",
    "userId": "uuid",
    "patronymic": "Сергеевна",
    "predictedName": "Сергей",
    "confidence": 0.98,
    "createdAt": "2026-06-27T10:00:00+00:00"
  }
}
```

Ошибки: `400`, `401`, `422`, `503`.

### `GET /api/history`

Заголовок:

```text
Authorization: Bearer session-token
```

Ответ `200`:

```json
{
  "items": [
    {
      "id": "uuid",
      "userId": "uuid",
      "patronymic": "Сергеевна",
      "predictedName": "Сергей",
      "confidence": 0.98,
      "createdAt": "2026-06-27T10:00:00+00:00"
    }
  ]
}
```

Ошибки: `401`.

## predictor_service

Базовый адрес: `http://localhost:8001`

### `POST /api/predict`

Запрос:

```json
{
  "patronymic": "Иванович"
}
```

Ответ `200`:

```json
{
  "patronymic": "Иванович",
  "gender": "male",
  "bestName": "Иван",
  "confidence": 0.98,
  "candidates": [
    {
      "name": "Иван",
      "confidence": 0.98,
      "reason": "Найдено точное соответствие в словаре распространенных отчеств."
    }
  ]
}
```

Если имя не найдено, ответ `422`:

```json
{
  "patronymic": "Неизвестное",
  "gender": "unknown",
  "bestName": null,
  "confidence": 0,
  "candidates": []
}
```

Ошибки: `400`, `422`.

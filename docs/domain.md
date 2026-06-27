# Предметная область

## Бизнес-контекст

Система помогает пользователю определить имя, от которого образовано русское отчество. Пользователь работает через сайт: регистрируется, входит в аккаунт, вводит отчество и получает результат с пояснением.

## Основные сценарии

1. Регистрация пользователя.
2. Вход пользователя.
3. Проверка отчества.
4. Просмотр истории проверок.
5. Обработка ошибки, если отчество пустое, слишком короткое или не подходит под правила.

## Сущности

- Пользователь: логин, имя, хеш пароля, дата создания.
- Сессия: токен, пользователь, дата создания.
- Отчество: входное значение для проверки.
- Результат определения: найденное имя, пол, уверенность, объяснение.
- Запись истории: пользователь, отчество, найденное имя, уверенность, дата.

## Бизнес-правила

1. Логин уникален.
2. Пароль хранится только в виде хеша.
3. Проверять отчество может только авторизованный пользователь.
4. Отчество должно состоять из букв или дефиса.
5. Точное словарное совпадение важнее общего правила по окончанию.
6. Если правило не найдено, сервис возвращает результат без имени и код `422`.
7. Каждый запрос авторизованного пользователя сохраняется в историю.

## Ограничения

- Прототип хранит данные в JSON-файлах.
- Сессии живут в памяти сервиса и сбрасываются после перезапуска.
- Определение имени не является стопроцентным: для редких отчеств используется вероятностное правило.

## ER-диаграмма

```mermaid
erDiagram
    USER ||--o{ SESSION : opens
    USER ||--o{ PREDICTION_HISTORY_ITEM : owns
    PATRONYMIC ||--o{ PREDICTION_RESULT : produces
    PREDICTION_RESULT ||--o{ NAME_CANDIDATE : contains

    USER {
        string id
        string username
        string fullName
        string passwordHash
        string createdAt
    }

    SESSION {
        string token
        string userId
        string createdAt
    }

    PREDICTION_HISTORY_ITEM {
        string id
        string userId
        string patronymic
        string predictedName
        float confidence
        string createdAt
    }

    PATRONYMIC {
        string value
    }

    PREDICTION_RESULT {
        string patronymic
        string gender
        string bestName
        float confidence
    }

    NAME_CANDIDATE {
        string name
        float confidence
        string reason
    }
```

## Диаграмма классов

```mermaid
classDiagram
    class User
    class Session
    class PredictionHistoryItem

    class UserRepository {
        <<interface>>
        add(user)
        find_by_username(username)
        find_by_id(user_id)
    }

    class JsonUserRepository
    class SessionRepository
    class InMemorySessionRepository
    class AuthService
    class PasswordHasher
    class PredictionClient
    class HttpPredictionClient
    class PredictionApplicationService

    class PatronymicRule {
        <<interface>>
        matches(patronymic)
        detect_gender(patronymic)
        apply(patronymic)
    }

    class KnownPatronymicRule
    class SuffixPatronymicRule
    class PatronymicAnalyzer
    class PredictionResult
    class NameCandidate

    UserRepository <|.. JsonUserRepository
    SessionRepository <|.. InMemorySessionRepository
    PredictionClient <|.. HttpPredictionClient
    PatronymicRule <|.. KnownPatronymicRule
    PatronymicRule <|.. SuffixPatronymicRule

    AuthService --> UserRepository
    AuthService --> SessionRepository
    AuthService --> PasswordHasher
    PredictionApplicationService --> PredictionClient
    PatronymicAnalyzer --> PatronymicRule
    PredictionResult --> NameCandidate
```

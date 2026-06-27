from abc import ABC, abstractmethod

from predictor_service.domain import Gender, NameCandidate


class PatronymicRule(ABC):
    @abstractmethod
    def matches(self, patronymic: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def detect_gender(self, patronymic: str) -> Gender:
        raise NotImplementedError

    @abstractmethod
    def apply(self, patronymic: str) -> list[NameCandidate]:
        raise NotImplementedError


class KnownPatronymicRule(PatronymicRule):
    def __init__(self, dictionary: dict[str, str]) -> None:
        self._dictionary = {key.lower(): value for key, value in dictionary.items()}

    def matches(self, patronymic: str) -> bool:
        return patronymic.lower() in self._dictionary

    def detect_gender(self, patronymic: str) -> Gender:
        lower = patronymic.lower()
        if lower.endswith(("ич", "ович", "евич")):
            return Gender.MALE
        if lower.endswith(("на", "чна")):
            return Gender.FEMALE
        return Gender.UNKNOWN

    def apply(self, patronymic: str) -> list[NameCandidate]:
        name = self._dictionary[patronymic.lower()]
        return [
            NameCandidate(
                name=name,
                confidence=0.98,
                reason="Найдено точное соответствие в словаре распространенных отчеств.",
            )
        ]


class SuffixPatronymicRule(PatronymicRule):
    def __init__(
        self,
        suffixes: tuple[str, ...],
        gender: Gender,
        confidence: float,
        reason: str,
        transform_stem,
    ) -> None:
        self._suffixes = suffixes
        self._gender = gender
        self._confidence = confidence
        self._reason = reason
        self._transform_stem = transform_stem

    def matches(self, patronymic: str) -> bool:
        return patronymic.lower().endswith(self._suffixes)

    def detect_gender(self, patronymic: str) -> Gender:
        return self._gender

    def apply(self, patronymic: str) -> list[NameCandidate]:
        lower = patronymic.lower()
        suffix = max(
            (suffix for suffix in self._suffixes if lower.endswith(suffix)),
            key=len,
        )
        stem = patronymic[: -len(suffix)]
        name = self._transform_stem(stem)
        if not name:
            return []
        return [
            NameCandidate(
                name=name,
                confidence=self._confidence,
                reason=self._reason,
            )
        ]


def title_name(value: str) -> str:
    return value[:1].upper() + value[1:].lower()


def plain_stem(stem: str) -> str:
    return title_name(stem)


def soft_y_stem(stem: str) -> str:
    return title_name(stem + "й")


def iy_stem(stem: str) -> str:
    return title_name(stem + "ий")


def a_stem(stem: str) -> str:
    return title_name(stem + "а")


DEFAULT_KNOWN_PATRONYMICS = {
    "алексеевич": "Алексей",
    "алексеевна": "Алексей",
    "андреевич": "Андрей",
    "андреевна": "Андрей",
    "артемович": "Артем",
    "артемовна": "Артем",
    "викторович": "Виктор",
    "викторовна": "Виктор",
    "владимирович": "Владимир",
    "владимировна": "Владимир",
    "дмитриевич": "Дмитрий",
    "дмитриевна": "Дмитрий",
    "евгеньевич": "Евгений",
    "евгеньевна": "Евгений",
    "иванович": "Иван",
    "ивановна": "Иван",
    "игоревич": "Игорь",
    "игоревна": "Игорь",
    "ильич": "Илья",
    "ильинична": "Илья",
    "кириллович": "Кирилл",
    "кирилловна": "Кирилл",
    "львович": "Лев",
    "львовна": "Лев",
    "максимович": "Максим",
    "максимовна": "Максим",
    "михайлович": "Михаил",
    "михайловна": "Михаил",
    "николаевич": "Николай",
    "николаевна": "Николай",
    "павлович": "Павел",
    "павловна": "Павел",
    "петрович": "Петр",
    "петровна": "Петр",
    "сергеевич": "Сергей",
    "сергеевна": "Сергей",
    "степанович": "Степан",
    "степановна": "Степан",
    "юльевич": "Юлий",
    "юльевна": "Юлий",
    "юрьевич": "Юрий",
    "юрьевна": "Юрий",
}


def default_rules() -> list[PatronymicRule]:
    return [
        KnownPatronymicRule(DEFAULT_KNOWN_PATRONYMICS),
        SuffixPatronymicRule(
            suffixes=("ьевич", "ьевна"),
            gender=Gender.MALE,
            confidence=0.7,
            reason="Применено правило для мягкой основы имени на -ий.",
            transform_stem=iy_stem,
        ),
        SuffixPatronymicRule(
            suffixes=("ович", "овна"),
            gender=Gender.MALE,
            confidence=0.78,
            reason="Применено общее правило для отчеств на -ович/-овна.",
            transform_stem=plain_stem,
        ),
        SuffixPatronymicRule(
            suffixes=("евич", "евна"),
            gender=Gender.MALE,
            confidence=0.62,
            reason="Применено общее правило для отчеств на -евич/-евна.",
            transform_stem=soft_y_stem,
        ),
        SuffixPatronymicRule(
            suffixes=("инична",),
            gender=Gender.FEMALE,
            confidence=0.58,
            reason="Применено редкое правило для женских отчеств на -инична.",
            transform_stem=a_stem,
        ),
    ]

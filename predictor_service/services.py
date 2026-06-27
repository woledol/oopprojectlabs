from predictor_service.domain import Gender, PatronymicRequest, PredictionResult
from predictor_service.rules import PatronymicRule, default_rules


class PatronymicValidationError(ValueError):
    pass


class PatronymicAnalyzer:
    def __init__(self, rules: list[PatronymicRule] | None = None) -> None:
        self._rules = rules or default_rules()

    def predict(self, request: PatronymicRequest) -> PredictionResult:
        patronymic = self._normalize(request.patronymic)
        for rule in self._rules:
            if rule.matches(patronymic):
                candidates = rule.apply(patronymic)
                gender = self._fix_gender(rule.detect_gender(patronymic), patronymic)
                return PredictionResult(
                    patronymic=patronymic,
                    gender=gender,
                    candidates=candidates,
                )
        return PredictionResult(
            patronymic=patronymic,
            gender=Gender.UNKNOWN,
            candidates=[],
        )

    def _normalize(self, patronymic: str) -> str:
        value = patronymic.strip().replace("ё", "е").replace("Ё", "Е")
        if not value:
            raise PatronymicValidationError("Отчество не должно быть пустым.")
        if len(value) < 4:
            raise PatronymicValidationError("Отчество слишком короткое.")
        if not all(ch.isalpha() or ch == "-" for ch in value):
            raise PatronymicValidationError("Отчество может содержать только буквы и дефис.")
        return value[:1].upper() + value[1:].lower()

    def _fix_gender(self, gender: Gender, patronymic: str) -> Gender:
        lower = patronymic.lower()
        if lower.endswith(("ович", "евич", "ич")):
            return Gender.MALE
        if lower.endswith(("овна", "евна", "ична", "инична")):
            return Gender.FEMALE
        return gender

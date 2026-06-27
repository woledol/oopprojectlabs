import unittest

from predictor_service.domain import Gender, PatronymicRequest
from predictor_service.services import PatronymicAnalyzer, PatronymicValidationError


class PatronymicAnalyzerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = PatronymicAnalyzer()

    def test_known_patronymic_has_high_confidence(self) -> None:
        result = self.analyzer.predict(PatronymicRequest("Сергеевна"))

        self.assertEqual("Сергей", result.best_name)
        self.assertEqual(Gender.FEMALE, result.gender)
        self.assertGreater(result.confidence, 0.9)

    def test_common_ovich_suffix(self) -> None:
        result = self.analyzer.predict(PatronymicRequest("Романович"))

        self.assertEqual("Роман", result.best_name)
        self.assertEqual(Gender.MALE, result.gender)

    def test_invalid_patronymic_raises_error(self) -> None:
        with self.assertRaises(PatronymicValidationError):
            self.analyzer.predict(PatronymicRequest("123"))


if __name__ == "__main__":
    unittest.main()

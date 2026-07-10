import unittest

from susurrate import dictionary


class TestApply(unittest.TestCase):
    def test_whole_word_case_insensitive(self):
        c = {"sesarite": "susurrate"}
        self.assertEqual(dictionary.apply("The Sesarite system.", c), "The susurrate system.")

    def test_no_partial_match(self):
        c = {"cat": "dog"}
        self.assertEqual(dictionary.apply("category catalog", c), "category catalog")

    def test_empty(self):
        self.assertEqual(dictionary.apply("hello", {}), "hello")


class TestLearnGuard(unittest.TestCase):
    """learn() diffs two texts without touching disk here — we pass corrections
    through apply() to check the guard, but learn() writes to DICT_PATH, so we
    only exercise the pure guard via _learnable."""

    def test_learns_mistranscription(self):
        # 'sesarite' is not a real word -> a genuine transcription fix
        self.assertTrue(dictionary._learnable("Sesarite", "susurrate"))

    def test_ignores_content_edit(self):
        # 'teal' is a real word -> changing it is a change of mind, not a fix
        self.assertFalse(dictionary._learnable("teal", "turquoise"))
        self.assertFalse(dictionary._learnable("Tuesday", "Wednesday"))

    def test_ignores_noop(self):
        self.assertFalse(dictionary._learnable("hello", "hello"))


class TestDefaults(unittest.TestCase):
    def test_ships_knowing_its_name(self):
        # a fresh install (no user file) already corrects the app's name
        self.assertEqual(dictionary.DEFAULTS["sesarite"], "Susurrate")
        merged = {**dictionary.DEFAULTS}
        self.assertEqual(dictionary.apply("great tool called sesarite", merged),
                         "great tool called Susurrate")


class TestPrompt(unittest.TestCase):
    def test_prompt_lists_right_forms(self):
        self.assertEqual(dictionary.prompt({"sesarite": "susurrate"}), "susurrate")


if __name__ == "__main__":
    unittest.main()

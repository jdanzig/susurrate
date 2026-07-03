import unittest

from susurrate.fmt import clean


class TestClean(unittest.TestCase):
    def test_fillers_removed(self):
        self.assertEqual(
            clean("Hello there, Um. This is a test. And, uh, it works."),
            "Hello there. This is a test. And it works.",
        )

    def test_annotations_stripped(self):
        self.assertEqual(clean("[BLANK_AUDIO] hello (coughs) world"), "Hello world.")

    def test_capitalize_and_terminate(self):
        self.assertEqual(clean("hello world"), "Hello world.")

    def test_question_kept(self):
        self.assertEqual(clean("is this working?"), "Is this working?")

    def test_empty(self):
        self.assertEqual(clean("[BLANK_AUDIO]"), "")
        self.assertEqual(clean(""), "")

    def test_whitespace_normalized(self):
        self.assertEqual(clean("hello   world ,  again"), "Hello world, again.")


if __name__ == "__main__":
    unittest.main()

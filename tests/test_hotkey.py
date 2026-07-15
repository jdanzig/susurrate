import unittest

from pynput.keyboard import Key

from susurrate.hotkey import Chord


class TestChord(unittest.TestCase):
    def test_single_key(self):
        c = Chord("alt_r")
        self.assertTrue(c.press(Key.alt_r))
        self.assertFalse(c.press(Key.alt_r))  # auto-repeat while held
        self.assertTrue(c.release(Key.alt_r))
        self.assertFalse(c.release(Key.alt_r))

    def test_chord_fires_when_complete(self):
        c = Chord("ctrl+win")
        self.assertFalse(c.press(Key.ctrl_l))  # half the chord: not yet
        self.assertTrue(c.press(Key.cmd))
        self.assertFalse(c.press(Key.cmd))  # auto-repeat while held
        self.assertTrue(c.release(Key.ctrl_l))  # any part breaks it
        self.assertFalse(c.release(Key.cmd))  # already broken

    def test_either_side_matches(self):
        c = Chord("ctrl+win")
        self.assertFalse(c.press(Key.ctrl_r))
        self.assertTrue(c.press(Key.cmd_r))

    def test_unrelated_keys_ignored(self):
        c = Chord("ctrl+win")
        c.press(Key.ctrl_l)
        self.assertFalse(c.press(Key.shift))
        self.assertFalse(c.release(Key.shift))
        self.assertTrue(c.press(Key.cmd))

    def test_partial_press_release_never_fires(self):
        c = Chord("ctrl+win")
        c.press(Key.ctrl_l)
        self.assertFalse(c.release(Key.ctrl_l))  # chord never completed

    def test_unknown_name_rejected(self):
        with self.assertRaises(SystemExit):
            Chord("ctrl+bogus")


if __name__ == "__main__":
    unittest.main()

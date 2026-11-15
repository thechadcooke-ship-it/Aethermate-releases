import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import vouch_filter as V


class VouchCommand(unittest.TestCase):
    def test_only_the_exact_command_vouches(self):
        self.assertTrue(V.comment_vouches("/vouch"))
        self.assertTrue(V.comment_vouches("  /VOUCH \n"))
        for body in ("looks good", "LGTM!", "I have not vouched for this", "please /vouch them", "/vouch and merge"):
            self.assertFalse(V.comment_vouches(body), body)

    def test_unvouched_pr_closes_and_vouched_stays(self):
        self.assertEqual(V.classify_pr("stranger", ["owner"])["action"], "close")
        self.assertEqual(V.classify_pr("owner", ["owner"])["action"], "keep")


if __name__ == "__main__":
    unittest.main()

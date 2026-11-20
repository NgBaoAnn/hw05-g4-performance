import unittest

from metrics import percentile, summarize


class WindowTests(unittest.TestCase):
    def test_half_open_window_and_business_failure(self):
        def row(t, elapsed, success):
            return dict(timeStamp=t, elapsed=elapsed, success=success, label="Login", bytes="30", allThreads="2")
        result=summarize([row(999,500,"true"),row(1000,4,"true"),row(1500,6,"false"),row(2000,300,"true")],1000,2000)
        self.assertEqual((result["samples"],result["errors"],result["success_rps"],result["p95_ms"]),(2,1,1,6))
        self.assertEqual(percentile(list(range(1,21))),19)
        with self.assertRaises(ValueError):
            summarize([],0,1000)


if __name__ == "__main__":
    unittest.main()

import unittest

from trending_digest.lifecycle import BrowserLifecycle


class BrowserLifecycleTests(unittest.TestCase):
    def test_refresh_and_multiple_tabs_do_not_stop_server(self):
        now = [0.0]
        lifecycle = BrowserLifecycle(grace_seconds=8, clock=lambda: now[0])
        self.assertFalse(lifecycle.should_stop())
        lifecycle.connect("first")
        lifecycle.connect("second")
        lifecycle.disconnect("first")
        now[0] = 20
        self.assertFalse(lifecycle.should_stop())
        lifecycle.disconnect("second")
        now[0] = 24
        self.assertFalse(lifecycle.should_stop())
        lifecycle.connect("refreshed")
        now[0] = 40
        self.assertFalse(lifecycle.should_stop())
        lifecycle.disconnect("refreshed")
        now[0] = 49
        self.assertTrue(lifecycle.should_stop())

    def test_unknown_unload_never_closes_an_unopened_server(self):
        lifecycle = BrowserLifecycle(grace_seconds=0)
        lifecycle.disconnect("unknown")
        self.assertFalse(lifecycle.should_stop())

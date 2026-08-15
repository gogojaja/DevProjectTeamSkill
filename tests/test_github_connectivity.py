import unittest

from tools.check_github_connectivity import (
    detect_failure_mode,
    get_remediation_steps,
    normalize_proxy_setting,
)
from tools.check_maintenance_scope import validate_scope


class GitHubConnectivityTests(unittest.TestCase):
    def test_detect_failure_mode_with_proxy_issue(self):
        output = """git push
nc: connection failed, SOCKS error 2
fatal: Could not read from remote repository.
"""
        self.assertEqual(detect_failure_mode(output), "proxy_or_network_block")

    def test_detect_failure_mode_with_auth_issue(self):
        output = """git push
remote: Permission to user/repo.git denied to other-user.
fatal: unable to access 'https://github.com/...': The requested URL returned error: 403
"""
        self.assertEqual(detect_failure_mode(output), "auth_or_permission")

    def test_normalize_proxy_setting_handles_localhost_proxies(self):
        value = "socks5h://localhost:64652"
        self.assertEqual(normalize_proxy_setting(value), "localhost:64652")

    def test_get_remediation_steps_includes_proxy_reset(self):
        steps = get_remediation_steps("proxy_or_network_block")
        self.assertTrue(any("unset HTTP_PROXY" in step or "unset https_proxy" in step for step in steps))
        self.assertTrue(any("git remote -v" in step for step in steps))

    def test_detect_failure_mode_with_ssh_443_close(self):
        output = """git push
Connection closed by 20.205.243.166 port 443
fatal: Could not read from remote repository.
"""
        self.assertEqual(detect_failure_mode(output), "proxy_or_network_block")

    def test_maintenance_scope_rejects_dev_project_root_without_explicit_authorization(self):
        ok, message = validate_scope("dev-project-team-skill", explicit_dev_root=False)
        self.assertFalse(ok)
        self.assertIn("explicit", message.lower())

    def test_maintenance_scope_allows_dev_project_root_with_explicit_authorization(self):
        ok, message = validate_scope("dev-project-team-skill", explicit_dev_root=True)
        self.assertTrue(ok)
        self.assertIn("allowed", message.lower())


if __name__ == "__main__":
    unittest.main()

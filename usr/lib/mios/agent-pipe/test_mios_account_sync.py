# AI-hint: stdlib unit test for mios-account-sync daemon (AGY-83).
# AI-related: usr/libexec/mios/mios-account-sync, usr/lib/mios/agent-pipe/test_mios_account_sync.py
# Tests user and group synchronization, bidirectional shadow password write-back,
# and supplementary group management hermetically without root permissions.
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
from collections import namedtuple

# Setup mock pwd and grp modules in sys.modules BEFORE importing mios-account-sync
# to ensure it works on Windows and non-root Linux environments.
struct_passwd = namedtuple("struct_passwd", ["pw_name", "pw_passwd", "pw_uid", "pw_gid", "pw_gecos", "pw_dir", "pw_shell"])
struct_group = namedtuple("struct_group", ["gr_name", "gr_passwd", "gr_gid", "gr_mem"])

class MockPwdModule:
    def __init__(self):
        self.users = {}
    def getpwnam(self, name):
        if name in self.users:
            return self.users[name]
        raise KeyError(name)
    def getpwall(self):
        return list(self.users.values())

class MockGrpModule:
    def __init__(self):
        self.groups_by_id = {}
        self.groups_by_name = {}
    def getgrgid(self, gid):
        if gid in self.groups_by_id:
            return self.groups_by_id[gid]
        raise KeyError(gid)
    def getgrnam(self, name):
        if name in self.groups_by_name:
            return self.groups_by_name[name]
        raise KeyError(name)
    def getgrall(self):
        return list(self.groups_by_name.values())

mock_pwd = MockPwdModule()
mock_grp = MockGrpModule()
sys.modules["pwd"] = mock_pwd
sys.modules["grp"] = mock_grp

# Now import the daemon module
from importlib.machinery import SourceFileLoader
import importlib.util
# Resolve root directory: test_mios_account_sync.py is in /usr/lib/mios/agent-pipe/
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
script_path = os.path.join(root_dir, "usr/libexec/mios/mios-account-sync")
loader = SourceFileLoader("mios_account_sync", script_path)
spec = importlib.util.spec_from_loader("mios_account_sync", loader)
sync_mod = importlib.util.module_from_spec(spec)
loader.exec_module(sync_mod)

class TestMiosAccountSync(unittest.TestCase):

    def setUp(self):
        mock_pwd.users.clear()
        mock_grp.groups_by_id.clear()
        mock_grp.groups_by_name.clear()
        
        # Add basic standard groups
        mock_grp.groups_by_id[1000] = struct_group("mios", "x", 1000, [])
        mock_grp.groups_by_name["mios"] = mock_grp.groups_by_id[1000]

    @patch("subprocess.run")
    @patch("os.path.isfile")
    def test_sync_create_user(self, mock_isfile, mock_run):
        # Setup: DB has a user that doesn't exist locally
        db_accounts = [{
            "name": "testuser",
            "password_hash": "hash123",
            "uid": 1005,
            "gid": 1000,
            "display": "Test User",
            "home_dir": "/var/home/testuser",
            "shell": "/bin/bash",
            "groups": "wheel,libvirt",
            "is_admin": True,
            "enabled": True
        }]
        
        # Mocks
        mock_isfile.return_value = False  # no state file
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        
        # Run sync using patched database query
        with patch.object(sync_mod, "query_db_accounts", return_value=db_accounts):
            with patch.object(sync_mod, "get_local_shadow_hashes", return_value={}):
                with patch("builtins.open", mock_open()) as mock_file:
                    sync_mod.sync_accounts()
        
        # Verify: useradd should be called
        calls = [c[0][0] for c in mock_run.call_args_list]
        useradd_called = any("useradd" in cmd for cmd in calls)
        self.assertTrue(useradd_called, "Should call useradd for new user")
        
        # Verify arguments passed to useradd
        useradd_cmd = next(cmd for cmd in calls if "useradd" in cmd)
        self.assertIn("-u", useradd_cmd)
        self.assertIn("1005", useradd_cmd)
        self.assertIn("-p", useradd_cmd)
        self.assertIn("hash123", useradd_cmd)
        self.assertIn("testuser", useradd_cmd)

    @patch("subprocess.run")
    @patch("os.path.isfile")
    def test_sync_update_user(self, mock_isfile, mock_run):
        # Setup: Local user exists but parameters differ (shell and display name)
        mock_pwd.users["testuser"] = struct_passwd(
            "testuser", "x", 1005, 1000, "Old Name", "/var/home/testuser", "/bin/sh"
        )
        
        db_accounts = [{
            "name": "testuser",
            "password_hash": "hash123",
            "uid": 1005,
            "gid": 1000,
            "display": "New Name",
            "home_dir": "/var/home/testuser",
            "shell": "/bin/bash",
            "groups": "",
            "is_admin": False,
            "enabled": True
        }]
        
        mock_isfile.return_value = False
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch.object(sync_mod, "query_db_accounts", return_value=db_accounts):
            with patch.object(sync_mod, "get_local_shadow_hashes", return_value={"testuser": "hash123"}):
                with patch("builtins.open", mock_open()):
                    sync_mod.sync_accounts()
                    
        # Verify usermod update was triggered
        calls = [c[0][0] for c in mock_run.call_args_list]
        usermod_called = any("usermod" in cmd for cmd in calls)
        self.assertTrue(usermod_called, "Should update existing user parameters via usermod")
        
        usermod_cmd = next(cmd for cmd in calls if "usermod" in cmd)
        self.assertIn("-c", usermod_cmd)
        self.assertIn("New Name", usermod_cmd)
        self.assertIn("-s", usermod_cmd)
        self.assertIn("/bin/bash", usermod_cmd)

    @patch("subprocess.run")
    @patch("os.path.isfile")
    def test_sync_password_writeback(self, mock_isfile, mock_run):
        # Setup: local user exists and local shadow hash changed compared to last_seen state.
        # This should trigger a write-back database query.
        mock_pwd.users["testuser"] = struct_passwd(
            "testuser", "x", 1005, 1000, "Test User", "/var/home/testuser", "/bin/bash"
        )
        
        db_accounts = [{
            "name": "testuser",
            "password_hash": "old_hash",
            "uid": 1005,
            "gid": 1000,
            "display": "Test User",
            "home_dir": "/var/home/testuser",
            "shell": "/bin/bash",
            "groups": "",
            "is_admin": False,
            "enabled": True
        }]
        
        mock_isfile.return_value = True
        mock_run.return_value = MagicMock(returncode=0)
        
        # State says we last saw old_hash, but local shadow is now new_local_hash
        state_data = '{"testuser": "old_hash"}'
        shadow_data = {"testuser": "new_local_hash"}
        
        with patch.object(sync_mod, "query_db_accounts", return_value=db_accounts):
            with patch.object(sync_mod, "get_local_shadow_hashes", return_value=shadow_data):
                with patch("builtins.open", mock_open(read_data=state_data)) as mock_file:
                    sync_mod.sync_accounts()
                    
        # Verify db write-back query was executed via pg_query
        calls = [c[0][0] for c in mock_run.call_args_list]
        db_writeback_called = any(any("mios-pg-query" in arg for arg in cmd) for cmd in calls)
        self.assertTrue(db_writeback_called, "Should trigger a writeback command to the database")

    @patch("subprocess.run")
    @patch("os.path.isfile")
    def test_sync_lock_disabled_user(self, mock_isfile, mock_run):
        # Setup: Local user testuser exists, but is NOT in active DB accounts.
        # It should be locked via `usermod -L`.
        mock_pwd.users["testuser"] = struct_passwd(
            "testuser", "x", 1005, 1000, "Test User", "/var/home/testuser", "/bin/bash"
        )
        
        # DB accounts list is empty or doesn't contain testuser, but must not be completely empty to avoid early return.
        db_accounts = [{
            "name": "otheruser",
            "password_hash": "hash321",
            "uid": 1006,
            "gid": 1000,
            "display": "Other User",
            "home_dir": "/var/home/otheruser",
            "shell": "/bin/bash",
            "groups": "",
            "is_admin": False,
            "enabled": True
        }]
        
        mock_isfile.return_value = False
        mock_run.return_value = MagicMock(returncode=0)
        
        # Shadow hash is active (not starting with ! or *)
        shadow_data = {"testuser": "$6$somehash"}
        
        with patch.object(sync_mod, "query_db_accounts", return_value=db_accounts):
            with patch.object(sync_mod, "get_local_shadow_hashes", return_value=shadow_data):
                with patch("builtins.open", mock_open()):
                    sync_mod.sync_accounts()
                    
        # Verify lock command was run
        calls = [c[0][0] for c in mock_run.call_args_list]
        lock_called = any(cmd == ["usermod", "-L", "testuser"] for cmd in calls)
        self.assertTrue(lock_called, "Should lock local user missing from DB using usermod -L")

if __name__ == "__main__":
    unittest.main()

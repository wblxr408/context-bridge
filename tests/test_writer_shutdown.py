"""A disabled scheduled task must not imply that its current writer exited."""
import msvcrt
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import install

class WriterShutdown(unittest.TestCase):
    def test_disabled_task_waits_for_writer_lock_and_owns_it_until_released(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            home = Path(temp)
            writer = (home / 'listener.lock').open('a+b')
            writer.seek(0)
            msvcrt.locking(writer.fileno(), msvcrt.LK_NBLCK, 1)
            completed = threading.Event()
            results = []
            errors = []
            def run():
                try:
                    results.append(install.quiesce())
                except Exception as error:
                    errors.append(error)
                finally:
                    completed.set()
            def scheduler(script):
                if 'Disable-' in script:
                    return ''
                return 'Running' if not (home / 'stop').exists() else 'Disabled'
            try:
                with patch.object(install, 'SERVICE', home), patch.object(install, 'powershell', scheduler):
                    thread = threading.Thread(target=run)
                    thread.start()
                    try:
                        self.assertFalse(completed.wait(0.15), 'Backup must wait for the active writer even when task is Disabled')
                    finally:
                        writer.seek(0)
                        msvcrt.locking(writer.fileno(), msvcrt.LK_UNLCK, 1)
                        writer.close()
                        thread.join(timeout=5)
                    self.assertFalse(errors)
                    self.assertTrue(completed.is_set())
                    previous, ownership = results[0]
                    self.assertEqual(previous, 'Running')
                    competitor = (home / 'listener.lock').open('a+b')
                    try:
                        competitor.seek(0)
                        with self.assertRaises(OSError):
                            msvcrt.locking(competitor.fileno(), msvcrt.LK_NBLCK, 1)
                    finally:
                        competitor.close()
                        ownership.close()
            finally:
                if not writer.closed:
                    writer.close()

if __name__ == '__main__':
    unittest.main()

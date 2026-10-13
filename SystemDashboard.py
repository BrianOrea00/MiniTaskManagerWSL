"""Compatibility launcher.

The dashboard now lives in the ``mini_task_manager`` package. This module is
kept so the existing command ``python SystemDashboard.py`` keeps working.
"""

from mini_task_manager.app import main

if __name__ == "__main__":
    main()

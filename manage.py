#!/usr/bin/env python3
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # MIRROR ONLY -- not part of the real project. This copy defaults to
    # config.settings_mirror so every command here talks to the throwaway
    # language_learning_mirror database. Without it, a forgotten `manage.py`
    # command would write to the real project's database. Set
    mirror_path = os.path.join(os.path.dirname(__file__), "config", "settings_mirror.py")
    if os.path.exists(mirror_path):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_mirror')
    else:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

from pathlib import Path
import subprocess
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

SCAN_DEFINITIONS = [
    {
        'name': 'pip-audit',
        'command': [sys.executable, '-m', 'pip_audit', '--format', 'json'],
        'output': BASE_DIR / 'pip_audit.json',
    },
    {
        'name': 'bandit',
        'command': [sys.executable, '-m', 'bandit', '-r', './filemanager', './config', '-x', './.venv-1,./staticfiles'],
        'output': BASE_DIR / 'bandit.json',
    },
    {
        'name': 'django-check',
        'command': [sys.executable, 'manage.py', 'check', '--deploy'],
        'output': BASE_DIR / 'django_check.txt',
    },
]


def run_scan(scan):
    print(f"Running {scan['name']}...")
    result = subprocess.run(
        scan['command'],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    scan['output'].write_text(result.stdout or result.stderr, encoding='utf-8')
    if result.returncode == 0:
        print(f"{scan['name']} completed successfully and wrote {scan['output']}")
    else:
        print(f"{scan['name']} finished with exit code {result.returncode}; see {scan['output']} for details")


if __name__ == '__main__':
    for scan in SCAN_DEFINITIONS:
        run_scan(scan)
    print('Security scan collection complete.')

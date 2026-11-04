"""Repeat the slice tests in both orders and preserve flakiness evidence."""
import json
import subprocess
import sys
from pathlib import Path

output = Path('docs/tasks/VT-094/evidence')
Path('.vt094-tmp').mkdir(exist_ok=True)
collected = subprocess.run([sys.executable, '-m', 'pytest', 'test/test_vt094_notifications.py', '--collect-only', '-q'],
                           capture_output=True, text=True, encoding='utf-8')
assert collected.returncode == 0, collected.stderr
nodes = [line for line in collected.stdout.splitlines() if line.startswith('test/') and '::' in line]
assert len(nodes) == 20
results = []
for index in range(3):
    ordered = list(reversed(nodes)) if index % 2 == 0 else nodes
    command = [sys.executable, '-m', 'pytest', *ordered, '-q', '--tb=short', f'--basetemp=.vt094-tmp/repeat{index}']
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
    (output/f'04_repeat_{index}.txt').write_text(result.stdout+result.stderr, encoding='utf-8')
    results.append({'run': index, 'order': 'reverse' if index % 2 == 0 else 'normal',
                    'collected': len(nodes), 'exit_code': result.returncode})
    print(json.dumps(results[-1]), flush=True)
    assert result.returncode == 0, result.stdout
(output/'repeat-results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')

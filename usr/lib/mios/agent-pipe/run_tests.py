import glob, subprocess, os, sys
os.environ.pop('MIOS_THEME_ROOT', None)
for k in list(os.environ.keys()):
    if k.startswith('MIOS_'):
        os.environ.pop(k)

fails = []
for t in sorted(glob.glob('test_mios_*.py')):
    print('Running', t)
    res = subprocess.run(['python3', t], capture_output=True, text=True)
    if res.returncode != 0:
        print('FAILED:', t)
        print(res.stderr)
        fails.append(t)

if fails:
    print('Failures:', fails)
    sys.exit(1)
else:
    print('All passed')

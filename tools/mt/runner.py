# ArtFlawless Studio - job runner for the translator training (temporary helper, started by hand with futtato.bat).
# Runs the .py files that appear in mt-train\jobs\ one after another with the Studio's own Python and writes their
# output to mt-train\logs\. A .studio file in jobs\ with the word stop, start or restart controls the Studio app.
# Nothing else is run, nothing listens on the network. Close this window (or create jobs\STOP) to end it.
import datetime, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))            # C:\ArtFlawlessStudio\mt-train
ROOT = os.path.dirname(HERE)                                  # C:\ArtFlawlessStudio
JOBS, DONE, LOGS = (os.path.join(HERE, d) for d in ('jobs', os.path.join('jobs', 'done'), 'logs'))
PY = os.path.join(ROOT, 'ComfyUI_windows_portable', 'python_embeded', 'python.exe')
LAUNCHER = os.path.join(ROOT, 'launcher', 'ArtFlow-Launcher.ps1')
STATUS = os.path.join(HERE, 'runner_status.json')
for d in (JOBS, DONE, LOGS):
    os.makedirs(d, exist_ok=True)


def now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def status(**kw):
    kw['heartbeat'] = now()
    tmp = STATUS + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(kw, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATUS)


def ps(cmd):
    return subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', cmd],
                          capture_output=True, text=True, timeout=120).stdout.strip()


def studio(action):
    out = []
    if action in ('stop', 'restart'):
        # only the Studio's own processes: its window, its launcher and the ComfyUI started from this folder
        root = ROOT.replace("'", "''")
        out.append(ps("Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'ArtFlawlessHost.exe') -or "
                      "($_.CommandLine -like '*" + root + "\\launcher\\ArtFlow-Launcher.ps1*') -or "
                      "($_.CommandLine -like '*" + root + "\\ComfyUI_windows_portable\\ComfyUI\\main.py*') } | "
                      "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $_.Name + ' ' + $_.ProcessId }"))
        time.sleep(5)
    if action in ('start', 'restart'):
        subprocess.Popen(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', LAUNCHER],
                         cwd=ROOT, creationflags=0x00000010 | 0x00000200)  # own console + process group (PowerShell quits at once when DETACHED)
        out.append('started')
    return '\n'.join(x for x in out if x)


def run(name):
    path = os.path.join(JOBS, name)
    log = os.path.join(LOGS, os.path.splitext(name)[0] + '.log')
    t0 = time.time(); started = now()
    status(state='running', job=name, started=started)
    print(now(), 'START', name, flush=True)
    with open(log, 'a', encoding='utf-8') as lf:
        lf.write('=== %s %s\n' % (now(), name)); lf.flush()
        if name.endswith('.studio'):
            action = open(path, encoding='utf-8').read().strip().lower()
            try:
                lf.write(studio(action) + '\n'); code = 0
            except Exception as e:
                lf.write('ERROR %s\n' % e); code = 1
        else:
            env = dict(os.environ, PYTHONUNBUFFERED='1', PYTHONIOENCODING='utf-8')
            p = subprocess.Popen([PY, '-s', path], cwd=HERE, stdout=lf, stderr=subprocess.STDOUT, env=env)
            while p.poll() is None:
                status(state='running', job=name, started=started, seconds=int(time.time() - t0))
                time.sleep(30 if time.time() - t0 > 30 else 2)
            code = p.returncode
        lf.write('=== exit %s after %d s\n' % (code, time.time() - t0))
    os.replace(path, os.path.join(DONE, time.strftime('%Y%m%d-%H%M%S-') + name))
    print(now(), 'END', name, 'exit', code, flush=True)
    return code


print('ArtFlawless Studio feladatfuttato - figyeli:', JOBS)
print('Leallitas: zard be ezt az ablakot.')
last = None
while True:
    if os.path.exists(os.path.join(JOBS, 'STOP')):
        os.remove(os.path.join(JOBS, 'STOP')); status(state='stopped'); break
    jobs = sorted(f for f in os.listdir(JOBS) if f.endswith(('.py', '.studio')) and os.path.isfile(os.path.join(JOBS, f)))
    if jobs:
        # wait until the file is complete (size stable), then run it
        p = os.path.join(JOBS, jobs[0]); s1 = os.path.getsize(p); time.sleep(2)
        if os.path.getsize(p) == s1:
            last = {'job': jobs[0], 'exit': run(jobs[0]), 'ended': now()}
    else:
        status(state='idle', last=last)
        time.sleep(5)

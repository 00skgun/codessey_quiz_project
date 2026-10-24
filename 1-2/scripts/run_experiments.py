#!/usr/bin/env python3
"""Run supplied Linux binary as an ordinary user. No binary inspection/modification."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import time
import pty
import threading

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    'oom-before': (50, 100, 'false'),
    'oom-after': (200, 100, 'false'),
    'cpu-before': (512, 10, 'false'),
    'cpu-after': (512, 100, 'false'),
    'deadlock-before': (512, 10, 'true'),
    'deadlock-after': (512, 10, 'false'),
}

def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds')

def run(name, seconds):
    memory, cpu, multi = CASES[name]
    folder = ROOT / 'evidence' / name
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'result.json').exists():
        raise SystemExit(f'Refusing to overwrite evidence: {folder}; move it first to rerun.')
    home = ROOT / 'runtime' / (name + '-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
    for child in ['upload_files', 'api_keys', 'logs']:
        (home / child).mkdir(parents=True, exist_ok=True)
    (home / 'api_keys' / 'secret.key').write_text('agent_api_key_test\n')
    env = os.environ.copy()
    env.update(AGENT_HOME=str(home), AGENT_PORT='15034',
               AGENT_UPLOAD_DIR=str(home / 'upload_files'),
               AGENT_KEY_PATH=str(home / 'api_keys'), AGENT_LOG_DIR=str(home / 'logs'),
               MEMORY_LIMIT=str(memory), CPU_MAX_OCCUPY=str(cpu), MULTI_THREAD_ENABLE=multi)
    binary = ROOT / 'bin' / ('agent-leak-app-arm64' if platform.machine() in ['aarch64', 'arm64'] else 'agent-leak-app-x86')
    binary.chmod(binary.stat().st_mode | 0o100)
    config = {k: env[k] for k in ['AGENT_HOME', 'AGENT_PORT', 'AGENT_UPLOAD_DIR', 'AGENT_KEY_PATH', 'AGENT_LOG_DIR', 'MEMORY_LIMIT', 'CPU_MAX_OCCUPY', 'MULTI_THREAD_ENABLE']}
    start, began = time.monotonic(), stamp()
    with (folder / 'app.log').open('w') as app, (folder / 'metrics.csv').open('w') as metrics, (folder / 'system.log').open('w') as system:
        system.write(f'run={name} started_at={began} kernel={platform.platform()} uid={os.getuid()}\n')
        system.flush()
        master, slave = pty.openpty()
        proc = subprocess.Popen([str(binary)], env=env, stdout=slave, stderr=slave, start_new_session=True)
        os.close(slave)
        def capture():
            try:
                while True:
                    chunk = os.read(master, 65536)
                    if not chunk:
                        break
                    app.write(chunk.decode('utf-8', errors='replace').replace('\r', ''))
                    app.flush()
            except OSError:
                pass  # Linux PTY EOF is EIO after all slave descriptors close.
            finally:
                os.close(master)
        reader = threading.Thread(target=capture)
        reader.start()
        # The distributed executable starts a wrapper parent and an application child.
        # Monitor the child that owns the Python workload, not the waiting wrapper.
        target = proc.pid
        for _ in range(100):
            children_path = Path(f'/proc/{proc.pid}/task/{proc.pid}/children')
            children = children_path.read_text().split() if children_path.exists() else []
            if children:
                target = int(children[0])
                break
            if proc.poll() is not None:
                break
            time.sleep(0.02)
        system.write(f'launcher_pid={proc.pid} application_pid={target}\n')
        system.flush()
        monenv = os.environ.copy()
        monenv['APP_LOG'] = str(folder / 'app.log')
        monitor = subprocess.Popen(['bash', str(ROOT / 'monitor.sh'), str(target), '0.5'], stdout=metrics, env=monenv)
        stopped = False
        try:
            while proc.poll() is None and time.monotonic()-start < seconds:
                system.write(f'\nSNAPSHOT timestamp={stamp()} pid={target}\n')
                system.flush()
                for command in [['ps', '-p', str(target), '-o', 'pid,ppid,etimes,stat,pcpu,pmem,rss,args'],
                                ['ps', '-L', '-p', str(target), '-o', 'pid,tid,stat,pcpu,wchan:32,comm'],
                                ['top', '-b', '-H', '-n', '1', '-p', str(target)]]:
                    subprocess.run(command, stdout=system, stderr=subprocess.STDOUT, check=False)
                time.sleep(2)
            alive = proc.poll() is None
            observed = time.monotonic()-start
            if alive:
                stopped = True
                system.write(f'\nHARNESS_STOP timestamp={stamp()} pid={proc.pid} reason=observation_window_end signal=SIGTERM\n')
                system.flush()
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            monitor.terminate()
            monitor.wait()
            reader.join(timeout=5)
        result = dict(case=name, pid=target, launcher_pid=proc.pid, started_at=began, ended_at=stamp(),
                      observation_seconds=round(observed, 3), alive_at_window_end=alive,
                      harness_stopped=stopped, returncode=proc.returncode, config=config)
    # Preserve application-owned files separately from captured stdout.
    import shutil
    shutil.copytree(home / 'logs', folder / 'application-files', dirs_exist_ok=True)
    (folder / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result), flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('cases', nargs='*', choices=list(CASES), default=list(CASES))
    parser.add_argument('--seconds', type=int, default=120)
    args = parser.parse_args()
    if platform.system() != 'Linux' or os.getuid() == 0:
        raise SystemExit('Use Linux/WSL as a non-root user.')
    for case in args.cases:
        run(case, args.seconds)

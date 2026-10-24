# [Bug] Deadlock - 멀티스레드 락 대기와 단일 스레드 회피 비교

## 1. Description (현상 설명)

MULTI_THREAD_ENABLE=true에서 PID가 살아 있으나 CPU/RSS와 로그 출력이 정체됐다. false에서는 작업과 자원 로그가 계속 진행됐다. 반복 스냅샷과 마지막 락 로그를 연결해 비교했다.

## 2. Evidence & Logs (증거 자료)

| 실행 ID | 앱 PID | 관측 초 | 최대 RSS MiB | 최대 구간 CPU % | 결과 |
|---|---:|---:|---:|---:|---|
| deadlock-before | 1059 | 76.101 | 17.8 | 7.98 | 교착 정체 (PID 생존, 수집기가 정리) |
| deadlock-after | 1191 | 76.125 | 518.0 | 15.93 | 관측 창 종료까지 PID 생존 (수집기가 정리) |

### deadlock-before (앱 PID 1059, 실행기 PID 1057)

![deadlock-before 저장 로그 캡처](../docs/log-captures/deadlock-before.png)

- 시작 UTC: `2026-10-19T18:20:46.647+00:00`
- 종료/관측 종료 UTC: `2026-10-19T18:22:08.539+00:00`
- 관측 시간: **76.101초**
- 판정: **교착 정체 (PID 생존, 수집기가 정리)** / returncode `-15` / 수집기 종료 `True`
- [실행 로그](../evidence/deadlock-before/app.log), [관제 CSV](../evidence/deadlock-before/metrics.csv), [ps·top 출력](../evidence/deadlock-before/system.log), [설정 및 결과](../evidence/deadlock-before/result.json)

```text
   ... Log directory is writable: /mnt/c/Users/user/Desktop/2026/codessey/1-2/runtime/deadlock-before-20261019T182046631910/logs
 >>> SYSTEM WARNING: POTENTIAL DEADLOCK IN CONCURRENT MODE.
2026-10-20 03:20:48,996 [WARNING] [AgentWorker] Initializing concurrent transaction processors...
2026-10-20 03:20:48,997 [WARNING] [System] CAUTION: Strict resource locking is enabled.
2026-10-20 03:20:54,018 [INFO] [Worker-Thread-1] Process Started. Attempting to lock [Shared_Memory_A]...
2026-10-20 03:20:54,018 [INFO] [AgentWorker][Worker-Thread-2] Process Started. Attempting to lock [Socket_Pool_B]...
2026-10-20 03:20:54,018 [INFO] [AgentWorker] Waiting for worker threads to complete transactions...
2026-10-20 03:20:54,019 [INFO] [AgentWorker][Worker-Thread-1] LOCK ACQUIRED: [Shared_Memory_A]. (Holding...)
2026-10-20 03:20:54,020 [INFO] [AgentWorker][Worker-Thread-2] LOCK ACQUIRED: [Socket_Pool_B]. (Holding...)
2026-10-20 03:20:54,022 [INFO] [AgentWorker][Worker-Thread-1] Processing critical data in Memory A...
2026-10-20 03:20:54,023 [INFO] [AgentWorker][Worker-Thread-2] Establishing network connections in Pool B...
2026-10-20 03:20:56,029 [INFO] [AgentWorker][Worker-Thread-2] Need resource [Shared_Memory_A] to write logs.
2026-10-20 03:20:56,030 [INFO] [AgentWorker][Worker-Thread-2] WAITING for [Shared_Memory_A]... (Status: BLOCKED)
2026-10-20 03:20:56,032 [INFO] [AgentWorker][Worker-Thread-1] Need resource [Socket_Pool_B] to finish job.
2026-10-20 03:20:56,033 [INFO] [AgentWorker][Worker-Thread-1] WAITING for [Socket_Pool_B]... (Status: BLOCKED)
```
### deadlock-after (앱 PID 1191, 실행기 PID 1189)

![deadlock-after 저장 로그 캡처](../docs/log-captures/deadlock-after.png)

- 시작 UTC: `2026-10-19T18:22:08.586+00:00`
- 종료/관측 종료 UTC: `2026-10-19T18:23:33.601+00:00`
- 관측 시간: **76.125초**
- 판정: **관측 창 종료까지 PID 생존 (수집기가 정리)** / returncode `-15` / 수집기 종료 `True`
- [실행 로그](../evidence/deadlock-after/app.log), [관제 CSV](../evidence/deadlock-after/metrics.csv), [ps·top 출력](../evidence/deadlock-after/system.log), [설정 및 결과](../evidence/deadlock-after/result.json)

```text
   ... Log directory is writable: /mnt/c/Users/user/Desktop/2026/codessey/1-2/runtime/deadlock-after-20261019T182208571393/logs
2026-10-20 03:22:10,933 [INFO] [Scheduler] Registered Tasks: ['Thread-A', 'Thread-B', 'Thread-C']
2026-10-20 03:22:10,935 [INFO] [Thread-B] Task Started. Calculating... (20%)
2026-10-20 03:22:10,986 [INFO] [Thread-B] Calculating... (40%)
2026-10-20 03:22:11,038 [INFO] [Thread-B] Calculating... (60%)
2026-10-20 03:22:11,090 [INFO] [Thread-B] Calculating... (80%)
... (중간 생략: 원본 app.log 참조) ...
2026-10-20 03:23:10,571 [INFO] [CpuWorker] Current Load: 7.42%
2026-10-20 03:23:12,260 [INFO] [MemoryWorker] Current Heap: 475MB
2026-10-20 03:23:12,682 [INFO] [CpuWorker] Peak reached (10.00%). Starting cooldown...
2026-10-20 03:23:13,689 [INFO] [CpuWorker] Current Load: 10.00%
2026-10-20 03:23:15,296 [INFO] [MemoryWorker] Current Heap: 500MB
2026-10-20 03:23:16,802 [INFO] [CpuWorker] Current Load: 8.20%
2026-10-20 03:23:18,333 [INFO] [MemoryWorker] Current Heap: 525MB
2026-10-20 03:23:18,334 [WARNING] [MemoryWorker] Memory Usage Reached Limit (525MB). Starting cleanup...
2026-10-20 03:23:19,915 [INFO] [CpuWorker] Current Load: 7.83%
2026-10-20 03:23:22,026 [INFO] [CpuWorker] Cooldown complete (5.00%). Resuming load increase...
2026-10-20 03:23:23,032 [INFO] [CpuWorker] Current Load: 5.00%
2026-10-20 03:23:23,419 [INFO] [MemoryWorker] Current Heap: 25MB
2026-10-20 03:23:28,084 [INFO] [CpuWorker] Peak reached (10.00%). Starting cooldown...
2026-10-20 03:23:29,090 [INFO] [CpuWorker] Current Load: 10.00%
2026-10-20 03:23:29,392 [INFO] [MemoryWorker] Current Heap: 50MB
2026-10-20 03:23:31,202 [INFO] [CpuWorker] Cooldown complete (5.00%). Resuming load increase...
2026-10-20 03:23:32,206 [INFO] [CpuWorker] Current Load: 5.00%
2026-10-20 03:23:32,421 [INFO] [MemoryWorker] Current Heap: 75MB
```

### 락 소유·대기 관계

| 스레드 | 이미 획득한 자원 | 추가로 기다리는 자원 | 로그 상태 |
|---|---|---|---|
| Worker-Thread-1 | Shared_Memory_A | Socket_Pool_B | WAITING / BLOCKED |
| Worker-Thread-2 | Socket_Pool_B | Shared_Memory_A | WAITING / BLOCKED |

Thread-1 → Socket_Pool_B → Thread-2 → Shared_Memory_A → Thread-1의 순환이 형성된다. 위의 원본 발췌에서 LOCK ACQUIRED와 WAITING 시각을 연결한 결과다.

### 마지막 스레드·프로세스 스냅샷 (UTC)

```text
Threads:   3 total,   0 running,   3 sleeping,   0 stopped,   0 zombie
%Cpu(s):  0.0 us,  0.4 sy,  0.0 ni, 99.6 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :  15634.1 total,  14455.2 free,    527.4 used,    651.5 buff/cache
MiB Swap:   4096.0 total,   4096.0 free,      0.0 used.  14907.4 avail Mem 

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
   1059 skgun00   30  10  170616  18244   9864 S   0.0   0.1   0:00.06 agent-l+
   1074 skgun00   30  10  170616  18244   9864 S   0.0   0.1   0:00.00 agent-l+
   1075 skgun00   30  10  170616  18244   9864 S   0.0   0.1   0:00.00 agent-l+

SNAPSHOT timestamp=2026-10-19T18:22:02.028+00:00 pid=1059
    PID    PPID ELAPSED STAT %CPU %MEM   RSS COMMAND
   1059    1057      70 SNl   0.0  0.1 18244 /mnt/c/Users/user/Desktop/2026/codessey/1-2/bin/agent-leak-app-x86
    PID     TID STAT %CPU WCHAN                            COMMAND
   1059    1059 SNl   0.0 futex_wait_queue                 agent-leak-app-
   1059    1074 SNl   0.0 futex_wait_queue                 agent-leak-app-
   1059    1075 SNl   0.0 futex_wait_queue                 agent-leak-app-
top - 03:22:02 up 8 min,  1 user,  load average: 0.08, 0.07, 0.03
Threads:   3 total,   0 running,   3 sleeping,   0 stopped,   0 zombie
%Cpu(s):  0.0 us,  0.0 sy,  0.0 ni,100.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :  15634.1 total,  14455.0 free,    527.6 used,    651.5 buff/cache
MiB Swap:   4096.0 total,   4096.0 free,      0.0 used.  14907.1 avail Mem 

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
   1059 skgun00   30  10  170616  18244   9864 S   0.0   0.1   0:00.06 agent-l+
   1074 skgun00   30  10  170616  18244   9864 S   0.0   0.1   0:00.00 agent-l+
   1075 skgun00   30  10  170616  18244   9864 S   0.0   0.1   0:00.00 agent-l+

SNAPSHOT timestamp=2026-10-19T18:22:04.194+00:00 pid=1059
    PID    PPID ELAPSED STAT %CPU %MEM   RSS COMMAND
   1059    1057      72 SNl   0.0  0.1 18244 /mnt/c/Users/user/Desktop/2026/codessey/1-2/bin/agent-leak-app-x86
    PID     TID STAT %CPU WCHAN                            COMMAND
   1059    1059 SNl   0.0 futex_wait_queue                 agent-leak-app-
   1059    1074 SNl   0.0 futex_wait_queue                 agent-leak-app-
   1059    1075 SNl   0.0 futex_wait_queue                 agent-leak-app-
top - 03:22:04 up 8 min,  1 user,  load average: 0.07, 0.07, 0.03
Threads:   3 total,   0 running,   3 sleeping,   0 stopped,   0 zombie
%Cpu(s):  0.0 us,  0.0 sy,  0.0 ni,100.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :  15634.1 total,  14455.0 free,    527.6 used,    651.5 buff/cache
MiB Swap:   4096.0 total,   4096.0 free,      0.0 used.  14907.1 avail Mem 

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
   1059 skgun00   30  10  170616  18244   9864 S   0.0   0.1   0:00.06 agent-l+
   1074 skgun00   30  10  170616  18244   9864 S   0.0   0.1   0:00.00 agent-l+
   1075 skgun00   30  10  170616  18244   9864 S   0.0   0.1   0:00.00 agent-l+

SNAPSHOT timestamp=2026-10-19T18:22:06.362+00:00 pid=1059
    PID    PPID ELAPSED STAT %CPU %MEM   RSS COMMAND
   1059    1057      74 SNl   0.0  0.1 18244 /mnt/c/Users/user/Desktop/2026/codessey/1-2/bin/agent-leak-app-x86
    PID     TID STAT %CPU WCHAN                            COMMAND
   1059    1059 SNl   0.0 futex_wait_queue                 agent-leak-app-
   1059    1074 SNl   0.0 futex_wait_queue                 agent-leak-app-
   1059    1075 SNl   0.0 futex_wait_queue                 agent-leak-app-
top - 03:22:06 up 8 min,  1 user,  load average: 0.07, 0.07, 0.03
Threads:   3 total,   0 running,   3 sleeping,   0 stopped,   0 zombie
%Cpu(s):  0.0 us,  0.0 sy,  0.0 ni,100.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :  15634.1 total,  14454.8 free,    527.8 used,    651.5 buff/cache
MiB Swap:   4096.0 total,   4096.0 free,      0.0 used.  14906.9 avail Mem 

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
   1059 skgun00   30  10  170616  18244   9864 S   0.0   0.1   0:00.06 agent-l+
   1074 skgun00   30  10  170616  18244   9864 S   0.0   0.1   0:00.00 agent-l+
   1075 skgun00   30  10  170616  18244   9864 S   0.0   0.1   0:00.00 agent-l+

HARNESS_STOP timestamp=2026-10-19T18:22:08.530+00:00 pid=1057 reason=observation_window_end signal=SIGTERM
```

### 마지막 10초 정체 관측

| UTC | PID | RSS KiB | 구간 CPU % | 로그 bytes |
|---|---:|---:|---:|---:|
| 2026-10-19T18:21:58.961+00:00 | 1059 | 18244 | 0.00 | 2717 |
| 2026-10-19T18:22:00.969+00:00 | 1059 | 18244 | 0.00 | 2717 |
| 2026-10-19T18:22:02.976+00:00 | 1059 | 18244 | 0.00 | 2717 |
| 2026-10-19T18:22:04.983+00:00 | 1059 | 18244 | 0.00 | 2717 |
| 2026-10-19T18:22:06.993+00:00 | 1059 | 18244 | 0.00 | 2717 |

## 3. Root Cause Analysis (원인 분석)

Worker-Thread-1은 Shared_Memory_A를 획득한 뒤 Socket_Pool_B를 기다리고, Worker-Thread-2는 Socket_Pool_B를 획득한 뒤 Shared_Memory_A를 기다린다. 각 락을 하나의 스레드만 갖는 상호 배제, 보유한 채 기다리는 점유 대기, 강제로 빼앗지 않는 비선점, 상대의 락을 기다리는 순환 대기가 함께 성립하는 구조다. 실제 ps -L에서 메인 스레드와 두 작업 스레드는 futex_wait_queue에서 대기했고 마지막 10초 RSS·로그 크기가 일정하며 구간 CPU는 0%였다. ps의 S 상태나 futex 대기만으로는 교착을 확정할 수 없어 락 로그와 진행 정체를 결합했다.

## 4. Workaround & Verification (조치 및 검증)

MULTI_THREAD_ENABLE을 true → false로 바꾸고 진행 로그·RSS·CPU 변화를 비교했다. MEMORY_LIMIT=512와 CPU_MAX_OCCUPY=10은 고정해 CPU 보호 종료의 간섭을 피했다. 단일 스레드로 순환 락 경쟁을 피하더라도 다른 장애까지 해결한 것은 아니다.

측정은 조건당 1회이며, 75초 관측 창 종료 시에는 수집기가 시작한 프로세스 그룹에 SIGTERM을 보낸다. `harness_stopped=true`는 앱 자체 종료 증거로 사용하지 않는다. 원본 로그의 종료 문구를 우선한다.

**검증 결론:** true에서 상반된 락 소유·대기와 정체를 관측했다. false에서는 같은 순환 대기 없이 작업 완료와 메모리·CPU 로그가 계속 진행됐고 메모리 캐시 정리 후 다시 증가하는 동작도 관측됐다. 두 실행은 수집기 종료 전까지의 관측이며 장기 무장애를 보장하지 않는다.

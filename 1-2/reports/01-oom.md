# [Bug] OOM - 메모리 한도 도달 시 MemoryGuard 강제 종료

## 1. Description (현상 설명)

메모리가 시간에 따라 계단 형태로 증가한 뒤 앱 MemoryGuard가 종료했다. MEMORY_LIMIT 외 설정을 고정하고 50MB와 200MB를 비교했다.

## 2. Evidence & Logs (증거 자료)

| 실행 ID | 앱 PID | 관측 초 | 최대 RSS MiB | 최대 구간 CPU % | 결과 |
|---|---:|---:|---:|---:|---|
| oom-before | 776 | 6.750 | 42.7 | 7.97 | MemoryGuard 강제 종료 |
| oom-after | 807 | 24.090 | 192.7 | 5.98 | MemoryGuard 강제 종료 |

### oom-before (앱 PID 776, 실행기 PID 773)

![oom-before 저장 로그 캡처](../docs/log-captures/oom-before.png)

- 시작 UTC: `2026-10-19T18:18:10.761+00:00`
- 종료/관측 종료 UTC: `2026-10-19T18:18:17.512+00:00`
- 관측 시간: **6.750초**
- 판정: **MemoryGuard 강제 종료** / returncode `-9` / 수집기 종료 `False`
- [실행 로그](../evidence/oom-before/app.log), [관제 CSV](../evidence/oom-before/metrics.csv), [ps·top 출력](../evidence/oom-before/system.log), [설정 및 결과](../evidence/oom-before/result.json)

```text
2026-10-20 03:18:13,150 [INFO] [MemoryWorker] Current Heap: 25MB
2026-10-20 03:18:16,175 [INFO] [MemoryWorker] Current Heap: 50MB
2026-10-20 03:18:16,177 [CRITICAL] [MemoryGuard] Memory limit exceeded (50MB >= 50MB) / (Recommend Over 256MB)
2026-10-20 03:18:16,178 [CRITICAL] [MemoryGuard] Self-terminating process 776 to prevent system instability.
>>> [SYSTEM] SELF-TERMINATED (Memory Limit Exceeded) <<<
```
### oom-after (앱 PID 807, 실행기 PID 805)

![oom-after 저장 로그 캡처](../docs/log-captures/oom-after.png)

- 시작 UTC: `2026-10-19T18:18:17.582+00:00`
- 종료/관측 종료 UTC: `2026-10-19T18:18:44.623+00:00`
- 관측 시간: **24.090초**
- 판정: **MemoryGuard 강제 종료** / returncode `-9` / 수집기 종료 `False`
- [실행 로그](../evidence/oom-after/app.log), [관제 CSV](../evidence/oom-after/metrics.csv), [ps·top 출력](../evidence/oom-after/system.log), [설정 및 결과](../evidence/oom-after/result.json)

```text
2026-10-20 03:18:19,948 [INFO] [MemoryWorker] Current Heap: 25MB
2026-10-20 03:18:22,986 [INFO] [MemoryWorker] Current Heap: 50MB
2026-10-20 03:18:26,020 [INFO] [MemoryWorker] Current Heap: 75MB
2026-10-20 03:18:29,050 [INFO] [MemoryWorker] Current Heap: 100MB
2026-10-20 03:18:32,084 [INFO] [MemoryWorker] Current Heap: 125MB
2026-10-20 03:18:35,133 [INFO] [MemoryWorker] Current Heap: 150MB
2026-10-20 03:18:38,165 [INFO] [MemoryWorker] Current Heap: 175MB
2026-10-20 03:18:44,152 [INFO] [MemoryWorker] Current Heap: 200MB
2026-10-20 03:18:44,153 [CRITICAL] [MemoryGuard] Memory limit exceeded (200MB >= 200MB) / (Recommend Over 256MB)
2026-10-20 03:18:44,154 [CRITICAL] [MemoryGuard] Self-terminating process 807 to prevent system instability.
>>> [SYSTEM] SELF-TERMINATED (Memory Limit Exceeded) <<<
```

## 3. Root Cause Analysis (원인 분석)

각 실행에서 Current Heap가 일정량씩 증가하고 MemoryGuard의 한도 초과 및 대상 PID 종료 로그가 이어진다. RSS도 함께 증가한다. 이는 메모리 누적과 앱 보호 정책에 의한 종료를 뒷받침한다. 외부 관측만으로 누수를 만드는 객체나 소스 위치는 확정할 수 없다. 이 종료를 커널 OOM killer 동작으로 단정하지 않는다.

## 4. Workaround & Verification (조치 및 검증)

MEMORY_LIMIT를 50 → 200MB로 높이면 더 오래 생존했으나 결국 같은 정책으로 종료했다. 메모리 누수의 근본 해결이 아닌 임시 조치다. 두 실행의 환경변수 CPU_MAX_OCCUPY=100, MULTI_THREAD_ENABLE=false는 동일하다.

측정은 조건당 1회이며, 75초 관측 창 종료 시에는 수집기가 시작한 프로세스 그룹에 SIGTERM을 보낸다. `harness_stopped=true`는 앱 자체 종료 증거로 사용하지 않는다. 원본 로그의 종료 문구를 우선한다.

**검증 결론:** 50MB에서 6.750초, 200MB에서 24.090초 관측 후 종료를 확인했다. 종료 직전 로그가 각각 50MB/200MB 도달을 기록하며 두 실행 모두 SELF-TERMINATED다. 생존 시간은 약 3.57배 늘었지만 영구 해결은 아니다.

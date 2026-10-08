# 리눅스 상태 점검 과제

WSL2 Ubuntu에서 앱을 실행하고, 상태·자원을 매분 점검해 로그를 남긴다. 필수 과제만 수행했다.

[수행 내역서](수행_내역서.md) · [monitor.sh](monitor.sh) · [전체 자료 ZIP](submission-with-captures.zip)

## 설명 순서

| 순서 | 내용 | 평가 문항 |
|---|---|---|
| 1 | [실행 환경](#step-1) | 과제 목적 |
| 2 | [SSH](#step-2) | 1-1, 3-1 |
| 3 | [방화벽](#step-3) | 1-2 |
| 4 | [계정·권한](#step-4) | 1-3, 2-3, 3-2 |
| 5 | [앱 실행](#step-5) | 1-4 |
| 6 | [모니터·로그](#step-6) | 1-5, 1-6, 2-1, 2-2, 3-4 |
| 7 | [cron](#step-7) | 1-7 |
| 8 | [앱 중단 시험](#step-8) | 1-5 |
| 9 | [경고·sudo 권한](#step-9) | 2-3, 3-3 |
| 10 | [로그 순환](#step-10) | 1-8, 2-4 |
| 11 | [장애 대응](#step-11) | 4-1~4-3 |

명령은 Ubuntu 터미널에서 실행한다. **A는 agent-admin으로 앱을 유지**, **B는 skgun00에서 설정과 모니터를 확인**한다.

<a id="step-1"></a>

### 1. 실행 환경

```bash
cat /etc/os-release
uname -r
ps -p 1 -o comm=
```

| 확인값 | 의미 |
|---|---|
| Ubuntu 22.04.5 LTS | 배포판 |
| microsoft-standard-WSL2 | WSL2 커널 |
| systemd | SSH·cron 등 서비스를 관리하는 프로세스 |

Docker 컨테이너 없이 WSL Ubuntu에 SSH·UFW·cron과 앱을 설치해 실행했다. PowerShell의 `wsl`은 로컬 Ubuntu를 여는 명령이며 SSH 접속은 아니다.

<a id="step-2"></a>

### 2. SSH

SSH는 암호화된 원격 접속 방법이다. `ssh`는 접속하는 클라이언트, `sshd`는 연결을 받는 서버다.

**설정 변경**

```bash
sudo nano /etc/ssh/sshd_config
```

첫 `Match` 앞의 전역 영역에서 다음 값을 설정한다. `#`가 붙으면 주석이므로 적용되지 않는다. 저장은 Ctrl+O → Enter, 종료는 Ctrl+X다.

```text
Port 20022
PermitRootLogin no
```

`/etc/ssh/sshd_config.d/*.conf`의 추가 설정도 확인한다. `PermitRootLogin`은 먼저 읽힌 값의 영향을 받고, `Port`는 여러 개가 지정될 수 있으므로 중복을 정리한다. [Ubuntu SSH 설정 매뉴얼](https://manpages.ubuntu.com/manpages/jammy/man5/sshd_config.5.html).

```bash
sudo ufw allow 20022/tcp
sudo /usr/sbin/sshd -t && sudo systemctl restart ssh
```

새 포트를 허용한 뒤 문법 검사가 성공할 때만 재시작한다. 원격 작업 중이면 기존 접속을 유지하고 새 창에서 변경 포트 접속을 확인한다.

**적용 확인**

```bash
sudo /usr/sbin/sshd -T | grep -E '^(port|permitrootlogin) '
sudo ss -ltnp | grep sshd
```

| 결과 | 의미 |
|---|---|
| `port 20022` | 적용 예정 SSH 포트 |
| `permitrootlogin no` | Root 직접 원격 로그인 금지 |
| `sshd`의 `:20022 LISTEN` | 실행 중인 SSH가 실제로 연결을 기다림 |

포트 변경은 기본 22번 대상의 단순 자동 접속 시도를 줄이는 보조 조치다. Root 직접 접속은 계정 탈취 시 바로 최고 권한을 주므로 막았다. `yes`는 Root 로그인을 허용하지만 비밀번호·키 인증을 없애지는 않는다.

![SSH 적용 설정과 실제 20022 LISTEN](captures/02-ssh.png)

<a id="step-3"></a>

### 3. 방화벽

```bash
sudo ufw status verbose
```

| 출력 | 의미 |
|---|---|
| `Status: active` | 방화벽 활성화 |
| `deny (incoming)` | 들어오는 연결 기본 차단 |
| `allow (outgoing)` | 나가는 연결 기본 허용 |
| `20022/tcp ALLOW IN` | SSH 접속 허용 |
| `15034/tcp ALLOW IN` | 앱 접속 허용 |
| `(v6)` | 같은 규칙의 IPv6 설정 |

`Anywhere`는 출발지 IP를 특정하지 않았다는 뜻이다. 허용 규칙은 지정한 두 TCP 포트뿐이다.

**방화벽 허용과 앱 LISTEN은 별개다.** 허용 규칙이 있어도 앱이 포트를 열지 않으면 서비스를 사용할 수 없다. UFW 확인은 리눅스 내부 정책의 증거이며 외부에서 WSL까지의 접속 성공을 증명하지는 않는다.

![UFW 활성화·기본 정책·허용 포트](captures/01-firewall.png)

<a id="step-4"></a>

### 4. 계정·권한

```bash
id agent-admin
id agent-dev
id agent-test
getent group agent-common agent-core
sudo ls -l /home/agent-admin/agent-app/bin/monitor.sh
```

| 계정 | common | core | 역할 |
|---|---|---|---|
| agent-admin | 포함 | 포함 | 앱·모니터·cron 실행 |
| agent-dev | 포함 | 포함 | monitor.sh 관리 |
| agent-test | 포함 | 미포함 | 공용 업로드 사용 |

`id`는 사용자 번호와 소속 그룹, `getent group`은 그룹 구성원을 보여 준다.

운영 스크립트는 **agent-dev:agent-core, 750**이다. 소유자는 rwx, 그룹은 r-x, 그 외는 접근 불가다. 디렉토리의 r은 목록 읽기, w는 생성·삭제, x는 경로 통과를 뜻한다.

```bash
sudo getfacl -p /home/agent-admin \
  /home/agent-admin/agent-app/upload_files \
  /home/agent-admin/agent-app/api_keys \
  /var/log/agent-app
```

- 홈의 common `--x`: 필요한 하위 경로까지 통과. 홈 목록 읽기 권한은 아님.
- setgid의 `s`: 새 파일이 디렉토리 그룹을 이어받도록 함.
- `default:` ACL: 새 항목의 기본 권한. `mask`: 그룹 계열 ACL의 유효 권한 상한.
- 실제 접근 시험: admin·dev는 업로드/키/로그 rwx, test는 업로드만 rwx.

키와 로그는 test의 업무에 필요하지 않아 core로 제한했다. 이것이 최소 권한 원칙이다.

![계정과 그룹](captures/03-accounts.png)

![디렉토리 소유자·그룹·권한](captures/04-1-directories.png)

![홈·앱·업로드 ACL](captures/04-2-acl-part-1.png)

![키·로그 ACL — 교체한 최신 캡처](captures/04-2-acl-part-2.png)

![실제 계정별 접근 결과](captures/04-3-access.png)

<a id="step-5"></a>

### 5. 앱 실행

터미널 A에서 실행한다. 이미 실행 중인 앱이 있으면 중복 실행하지 않는다.

```bash
sudo -iu agent-admin
source /home/agent-admin/agent-app/agent-env.sh
whoami
env | grep -E '^(AGENT_HOME|AGENT_PORT|AGENT_UPLOAD_DIR|AGENT_KEY_PATH|AGENT_LOG_DIR)='
cd "$AGENT_HOME"
"$AGENT_HOME/agent-app-linux-x86"
```

`sudo -iu`는 계정과 로그인 환경을 전환한다. `source`는 설정을 현재 셸에 읽고, `export`된 변수는 앱에 전달된다. 절대 경로 실행은 모니터의 프로세스 검색 조건과 맞추기 위한 것이다.

| 변수 | 값 |
|---|---|
| AGENT_HOME | `/home/agent-admin/agent-app` |
| AGENT_PORT | `15034` |
| AGENT_UPLOAD_DIR | 앱 아래 `upload_files` |
| AGENT_KEY_PATH | 앱 아래 `api_keys` **디렉토리** |
| AGENT_LOG_DIR | `/var/log/agent-app` |

Boot는 **계정 → 환경 변수 → 필수 파일 → 포트 사용 가능 여부 → 로그 쓰기 권한** 순서로 검사한다. 이후 앱이 실행되며 INFO 로그가 계속 나오는 것은 정상이다. 점검은 터미널 B에서 한다.

```bash
sudo ss -ltnp '( sport = :15034 )'
```

`0.0.0.0:15034 LISTEN`은 앱이 IPv4 인터페이스에서 연결을 기다린다는 뜻이다.

**해결한 오류:** AGENT_KEY_PATH에 키 파일 경로를 넣었더니 앱이 디렉토리를 요구했다. 공용 `agent-env.sh`를 api_keys 디렉토리로 수정했다. 아래 초기 캡처의 파일 경로는 최종 설정이 아니다.

![초기 AGENT 변수 미출력](captures/05-env-initial.png)

![초기 실행 계정·환경 변수·파일](captures/05-1-environment.png)

![키 경로 불일치 오류](captures/05-key-path-error.png)

![공용 환경 파일의 키 경로 수정](captures/05-key-path-config-update.png)

![수정 후 Boot 5단계 OK](captures/05-2-boot.png)

**남은 증거:** 위 캡처에는 `Agent READY`가 잘려 있다. 해당 문구가 보이는 캡처를 추가해야 한다.

![실행 중 앱 자체 로그](captures/05-app-runtime.png)

![앱 15034 LISTEN](captures/05-3-listen.png)

<a id="step-6"></a>

### 6. 모니터·로그

```bash
sudo -iu agent-admin /home/agent-admin/agent-app/bin/monitor.sh
echo "종료 코드: $?"
sudo -u agent-admin tail -n 5 /var/log/agent-app/monitor.log
```

`$?`는 바로 앞 명령의 종료 코드다. 모니터 실행 직후 확인해야 한다. `tail -n 5`는 마지막 다섯 줄을 읽는다.

| 검사·측정 | 구현 | 이유 |
|---|---|---|
| 앱 PID | `pgrep -f -x` | 전체 실행 명령행이 일치하는 PID 식별 |
| 포트·소유 PID | `ss -H -ltnp` | LISTEN 확인 후 앱 PID와 비교 |
| CPU | `/proc/stat` 두 번 읽기 | 1초간 누적 시간 차이로 계산 |
| MEM | `/proc/meminfo` | MemAvailable 기준 사용률 |
| DISK | `df -P /` | 루트 파일시스템 사용률 추출 |

```text
CPU = (전체 시간 증가량 − 유휴 시간 증가량) / 전체 시간 증가량 × 100
MEM = (MemTotal − MemAvailable) / MemTotal × 100
```

CPU의 유휴 시간에는 idle과 iowait를 사용한다. 전체 증가량 1000, 유휴 증가량 800이면 CPU는 20%다. **자원 값은 앱 하나가 아니라 리눅스 전체 기준**이다.

프로세스만 확인하면 초기화 실패를 놓치고, 포트만 확인하면 다른 앱을 정상으로 오인할 수 있어 둘을 비교한다. 정상 결과는 종료 코드 0이다.

```text
[2026-10-08 22:33:02] PID:4185,4186 CPU:1.2% MEM:5.6% DISK_USED:7%
```

시간·필드·순서를 고정해 비교와 값 추출을 쉽게 했다. `>>`는 기존 내용 뒤에 추가하고 `>`는 덮어쓴다. 정상 점검은 `>>`로 누적한다.

![정상 점검과 종료 코드 0](captures/06-1-monitor-ok.png)

![운영 스크립트 권한과 로그 누적](captures/07-1-log.png)

![제출 복사본 — skgun00 소유·644, 운영 원본 750과 구분](captures/10-source-copy.png)

<a id="step-7"></a>

### 7. cron

cron은 예약 실행 도구다. admin의 작업 목록을 확인·편집한다.

```bash
sudo crontab -u agent-admin -l
sudo crontab -u agent-admin -e
```

`-u`는 대상 계정, `-l`은 조회, `-e`는 편집이다. 기존 모니터 줄을 수정하고 다른 작업은 유지한다. nano 저장은 Ctrl+O → Enter → Ctrl+X다.

```cron
* * * * * /bin/bash /home/agent-admin/agent-app/bin/monitor.sh 2>&1 | /usr/bin/logger -t agent-monitor-study # agent-app-monitor-managed
```

| 부분 | 의미 |
|---|---|
| 다섯 시간 필드 | 분·시·일·월·요일 |
| `* * * * *` | 매분 |
| `*/5 * * * *` | 매시간 0·5·10…55분 |
| `0 * * * *` | 매시간 정각 |
| `/bin/bash`와 절대 경로 | Bash로 지정 스크립트 실행 |
| `2>&1 \| logger` | 오류·일반 출력을 시스템 로그로 전달 |

이번 과제는 매분 설정이다. 사용자 crontab에는 사용자 이름 필드를 추가하지 않는다. 저장한 변경은 cron이 읽으므로 매번 재시작할 필요는 없다. [Ubuntu crontab 매뉴얼](https://manpages.ubuntu.com/manpages/jammy/man5/crontab.5.html).

**자동 실행 확인:** 앱을 유지하고 아래 값을 기록한다. 수동 실행 없이 다음 분이 지난 뒤 다시 확인한다.

```bash
date '+%Y-%m-%d %H:%M:%S'
sudo -u agent-admin wc -l /var/log/agent-app/monitor.log
sudo -u agent-admin tail -n 3 /var/log/agent-app/monitor.log
```

| 확인 시각 | 줄 수 | 마지막 기록 |
|---|---|---|
| 22:32:13 | 20 | 22:32:02 |
| 22:33:10 | 21 | 22:33:02 |

새 시각의 기록과 줄 수 증가가 자동 실행의 증거다. 순환이 발생하면 줄 수가 줄 수 있으므로 시각도 확인한다.

![cron 등록·기준 로그](captures/08-1-cron-before.png)

![다음 분 자동 증가](captures/08-2-cron-after.png)

실행되지 않으면 앱 상태 → `systemctl is-active cron` → 작업 경로·권한 → 실행 출력을 확인한다.

```bash
sudo journalctl -t agent-monitor-study --since '5 minutes ago' --no-pager
```

cron은 터미널의 변수를 그대로 받지 않는다. 스크립트 내부에서 환경 파일과 PATH를 읽는다. WSL이 종료되면 cron도 실행되지 않는다. logger의 종료 코드는 모니터의 0/1과 구분한다.

<a id="step-8"></a>

### 8. 앱 중단 시험

cron 증가 확인을 끝낸 뒤 **A에서 Ctrl+C**로 앱을 중단하고 B에서 실행한다.

```bash
sudo -iu agent-admin /home/agent-admin/agent-app/bin/monitor.sh
echo "종료 코드: $?"
```

실제 결과는 `App process is not running.`과 종료 코드 1이다. 상태 점검에서 끝나므로 정상 자원 로그는 추가하지 않는다. 오류는 터미널로, cron 실행이면 logger로 전달된다.

코드에서는 **프로세스 없음·포트 LISTEN 없음·앱과 소유 PID 불일치**를 실패로 처리한다. 실제 중단 캡처로 검증한 것은 프로세스 부재다.

![앱 중단 후 오류와 종료 코드 1](captures/06-2-monitor-failure.png)

시험 후 A에서 `"$AGENT_HOME/agent-app-linux-x86"`로 복구하고, B에서 정상 종료 코드 0을 확인한다.

<a id="step-9"></a>

### 9. 경고·sudo 권한

```bash
sudo -l -U agent-admin
```

admin에게 비밀번호 없이 허용된 명령은 **`/usr/sbin/ufw status`뿐**이다. 모니터는 `sudo -n`으로 조회해 비밀번호 입력을 기다리지 않는다.

![UFW 상태 조회 전용 sudo 규칙](captures/06-4-sudo-policy.png)

| 경고 | 조건 |
|---|---|
| CPU | 20% 초과 |
| MEM | 10% 초과 |
| DISK_USED | 80% 초과 |
| UFW | 비활성·조회 실패 |

경고 후에도 다른 상태 수집과 기록을 계속한다. 앱·포트 부재는 핵심 실패여서 종료하지만, 경고만으로 끝내면 남은 정보를 놓치기 때문이다.

가상 CPU 21%, MEM 11%, DISK 81%와 inactive 응답으로 경고 네 개, 계속 실행, 종료 코드 0을 확인했다. 실제 방화벽과 자원 상태를 바꾼 시험은 아니다.

![경고 후 계속 실행과 종료 코드 0](captures/06-3-warnings.png)

<details>
<summary>경고 시험 명령</summary>

```bash
sudo -iu agent-admin /bin/bash <<'BASH'
set -e
source /home/agent-admin/agent-app/bin/monitor.sh
warn_if_over CPU 21.0 20
warn_if_over MEM 11.0 10
warn_if_over DISK_USED 81 80
ufw_status() { printf 'Status: inactive\n'; }
check_firewall
echo '[TEST] 경고 후에도 계속 실행됨'
BASH
echo "테스트 종료 코드: $?"
```

source로 읽으면 함수만 정의한다. UFW 응답 재정의는 이 시험 셸에만 적용된다.

</details>

<a id="step-10"></a>

### 10. 로그 순환

**10MiB = 10,485,760바이트**, **현재 로그 1개 + 백업 9개 = 최대 10개**다. 새 줄을 쓰기 전에 크기를 검사한다.

```text
기존 .9 삭제
→ .8부터 .1까지 번호를 하나씩 뒤로 이동
→ 현재 monitor.log를 .1로 이동
→ 새 monitor.log에 기록
```

큰 번호부터 옮겨 백업 덮어쓰기를 막는다. `.1`이 최신, `.9`가 가장 오래된 백업이다. `flock`은 수동 실행과 cron이 동시에 기록·순환하는 것을 막는다.

임시 파일 시험에서 새 로그 14바이트, `.1` 10,485,760바이트, 파일 수 10개, PASS와 종료 코드 0을 확인했다. 이 제한은 monitor.log 계열에만 적용된다.

![로그 순환·10개 유지 시험](captures/09-log-rotation.png)

<details>
<summary>로그 순환 시험 명령</summary>

```bash
sudo -iu agent-admin /bin/bash <<'BASH'
set -e
source /home/agent-admin/agent-app/bin/monitor.sh
rotation_dir=$(mktemp -d /tmp/agent-rotation-test.XXXXXX)
LOG_FILE="$rotation_dir/monitor.log"
for n in {1..9}; do
    printf 'backup-%s\n' "$n" > "$LOG_FILE.$n"
done
truncate -s $((10*1024*1024)) "$LOG_FILE"
write_log 'rotation-test'
stat -c '%n : %s bytes' "$LOG_FILE" "$LOG_FILE".[1-9]
file_count=$(find "$rotation_dir" -type f -name 'monitor.log*' | wc -l)
echo "로그 파일 수: $file_count"
test "$file_count" -eq 10
test "$(cat "$LOG_FILE.9")" = 'backup-8'
cat "$LOG_FILE"
echo '[PASS] 용량 기준 순환과 최대 10개 유지 확인'
BASH
echo "테스트 종료 코드: $?"
```

LOG_FILE을 시험 셸에서만 임시 경로로 바꾸므로 운영 로그는 변경하지 않는다.

</details>

<a id="step-11"></a>

### 11. 장애 대응

| 질문 | 답변 |
|---|---|
| Nginx로 바뀐다면? | master·worker 구조에 맞게 프로세스 식별, 서비스 포트, 로그 경로·권한, 임계값을 바꾼다. 웹 응답까지 확인하려면 HTTP 검사를 추가한다. |
| 프로세스는 있는데 포트가 없다면? | 실행 명령 → ss의 LISTEN·소유 PID → 앱 로그 → 설정·포트 충돌·권한 순서로 확인한다. 초기화 실패와 bind 실패를 찾는다. |
| 로컬은 정상인데 외부 연결이 안 되면? | 방화벽과 WSL 네트워크 경로를 확인한다. 방화벽 허용으로 앱의 소켓 생성 실패를 해결할 수는 없다. |
| 로그로 디스크가 찬다면? | 커지는 파일을 찾고 필요한 증거를 보존한 뒤 정리·출력 축소를 한다. 이후 모든 로그의 순환 정책과 디스크 감시를 점검한다. |

위 내용은 대응 방법 설명이며 Nginx 전환이나 보너스 기간별 압축·삭제를 구현한 것은 아니다. 문항별 답변은 [수행 내역서](수행_내역서.md)에 있다.

# 컴퓨터가 알아서 자기 상태를 점검하게 만들기

첨부 PDF의 실제 과제는 **Linux/OS 기초: 보안 설정 + 계정/권한 + Bash 시스템 관제**입니다. 작업 위치는 이 저장소의 `1-1/`이며, 실행 대상은 이 PC에 설치된 **WSL2 Ubuntu-22.04**입니다. Windows의 Git Bash에서는 실제 시스템 점검을 실행하지 않습니다.

최종 제출물은 [monitor.sh](monitor.sh)와 [수행내역서.md](수행내역서.md)입니다. 내역서에 연결된 `evidence/`도 함께 보관하세요. **필수 설정/구현/실제 실행 검증은 완료했습니다.** 앱 5단계 `[OK]`, `Agent READY`, cron의 70초 동안 1줄→2줄 증가를 확인했습니다. 제공 앱과 PDF의 키 경로/파일명 차이는 아래 호환 처리 설명을 확인하세요.

**지금 본인이 할 일:** 수행 내역서와 코드를 읽고 설명할 내용을 익힌 다음, 아래 확인 명령을 직접 실행하고 과제 사이트에 제출하세요. 설치 과정을 다시 할 필요는 없습니다.

PowerShell에서 `wsl -d Ubuntu-22.04`를 실행한 뒤, 열린 Ubuntu 터미널에서:

```bash
sudo systemctl status agent-app cron ssh --no-pager
sudo journalctl -u agent-app -b --no-pager -n 60
sudo -u agent-admin -H /home/agent-admin/agent-app/bin/monitor.sh
sudo -u agent-admin -H /home/agent-admin/agent-app/bin/report.sh
```

앱을 터미널에 새로 띄우려면 기존 서비스와 포트가 겹치지 않도록 아래 3번의 종료/시작 순서를 따르세요.

## 파일 안내

| 파일 | 역할 |
| --- | --- |
| `monitor.sh` | 필수: 프로세스·포트·방화벽·CPU/MEM/DISK 점검, 로그 기록 및 순환 |
| `apply-mission.sh` | 준비된 설정 전체 적용 및 실제 실행 증거 수집; 이미 완료된 환경은 재실행 불필요 |
| `report.sh` | 선택 보너스 1: 평균·최대·최소·시각·샘플 수, 시간 범위 필터 |
| `setup.sh` | 제공 앱 설치, 계정/그룹/ACL/환경 변수 및 스크립트 권한 구성 |
| `configure-security.sh` | 로컬 실습 환경에서 SSH 20022, root 로그인 차단, UFW 적용 |
| `run-app.sh` | 환경 변수를 읽고 제공 앱을 agent-admin으로 실행 |
| `install-cron.sh` | agent-admin crontab에 매분 실행 등록, 다른 cron 작업 보존 |
| `agent-app.service` | 일반 계정으로 앱을 계속 실행하기 위한 systemd 서비스 |
| `verify-permissions.sh` | 세 계정의 실제 읽기/쓰기와 agent-test 접근 거부 확인 |
| `collect-evidence.sh` | 실제 설정/모니터/cron 상태를 출력하는 증거 수집 도구 |
| `tests/run-tests.sh` | 격리된 합성 데이터 테스트. 과제 실행 증거와 구분 |

## 처음부터 재현하는 순서

이미 설정이 완료되어 있으면 아래 설치 과정을 반복할 필요가 없습니다. 현재 상태는 `수행내역서.md`를 먼저 확인하세요.

### 1. Ubuntu 열기와 제공 앱 준비

Windows PowerShell에서:

```powershell
wsl -d Ubuntu-22.04
```

이후 명령은 **Ubuntu 터미널**에서 실행합니다. 시연과 cron 확인 중에는 이 터미널을 열어 두세요. WSL에서는 systemd 서비스 자체가 인스턴스의 계속 실행을 보장하지 않습니다. [Microsoft WSL 설명](https://learn.microsoft.com/en-us/windows/wsl/systemd)

```bash
cd /mnt/c/Users/user/Desktop/2026/codessey/1-1
sudo apt-get update
sudo apt-get install -y acl openssh-server ufw cron python3 procps iproute2 sudo util-linux
```

사용자가 제공한 `agent-app.zip`에서 x86 실행 파일을 `provided/agent-app-linux-x86`에 추출했습니다. 새 환경에서 압축을 다시 풀려면 `unzip`을 사용하거나 Windows 탐색기에서 압축을 풀어 이 위치에 놓으세요. ARM 환경에서는 `uname -m`을 확인하고 원본 ZIP의 `agent-app-linux-arm64`를 사용합니다.

```bash
sudo bash setup.sh "$PWD/provided/agent-app-linux-x86"
sudo bash verify-permissions.sh
```

계정 암호를 임의로 만들지 않습니다. 로컬 실습은 `sudo -u agent-admin`으로 실행합니다. `agent-admin/dev/test`에 전체 sudo 권한도 부여하지 않습니다. 관리자의 기존 Ubuntu 계정에서 필요한 설치 명령만 `sudo`로 수행합니다.

### 2. SSH와 방화벽 설정

**로컬 WSL/VM 콘솔에서** 실행하세요. 원격 SSH 세션에서 포트를 바꾸면 재접속이 필요하므로 이 스크립트는 원격 실행을 중단합니다.

```bash
sudo bash configure-security.sh
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T | awk '$1=="port" || $1=="permitrootlogin"'
sudo ss -ltnp 'sport = :20022'
sudo ufw status verbose
```

기대 설정은 `port 20022`, `permitrootlogin no`, UFW `Status: active`, 기본 incoming deny, 사용자 지정 인바운드 허용 규칙 `20022/tcp`와 `15034/tcp`입니다. IPv4/IPv6가 모두 켜져 있으면 같은 두 규칙이 `(v6)`로 한 번씩 더 표시됩니다. UFW의 기본 루프백·연결 추적 규칙은 유지합니다.

기존의 다른 UFW 규칙이 있으면 스크립트가 적용 전에 멈춥니다. `sudo ufw status numbered`로 확인하고, 필요 없는 규칙만 `sudo ufw delete 번호`로 지운 뒤 다시 실행하세요. 번호는 삭제할 때마다 바뀌므로 목록을 다시 확인합니다. 기존 서비스를 쓰는 서버에는 무조건 적용하지 마세요.

### 3. 제공 앱 실행

**제공 앱과 PDF의 불일치:** PDF 4쪽은 `AGENT_KEY_PATH=$AGENT_HOME/api_keys/t_secret.key`라고 안내하지만, 실제 제공 x86 실행 파일은 키 **디렉터리**를 요구하고 그 안의 **`secret.key`**를 읽습니다. `agent-env.sh`에는 PDF의 파일 경로를 유지하고, `run-app.sh`가 제공 바이너리를 실행할 때만 `dirname`으로 디렉터리로 변환합니다. `setup.sh`는 `secret.key -> t_secret.key` 심볼릭 링크를 추가합니다. 따라서 원본 바이너리와 PDF가 요구한 `t_secret.key` 및 그 내용은 그대로 유지합니다. Python 소스를 사용하는 경우에는 변환하지 않습니다. 제출 내역서에 이 차이와 실제 검증 결과를 함께 기재합니다.

첫 확인은 터미널에서 실행하면 Boot Sequence를 직접 볼 수 있습니다. 이미 `agent-app` 서비스가 실행 중이면 먼저 `sudo systemctl stop agent-app`으로 중지하세요. 그 뒤 아래 명령을 실행합니다.

```bash
sudo -u agent-admin -H /home/agent-admin/agent-app/bin/run-app.sh
```

5단계가 모두 `[OK]`이고 마지막에 `Agent READY`가 보여야 합니다. 이 터미널에서는 `Ctrl+C`로 종료합니다. 다른 터미널에서 `sudo ss -ltnp 'sport = :15034'`로 `0.0.0.0:15034`를 확인하세요.

cron 검증 중에도 앱을 유지하려면, 터미널 실행을 먼저 종료한 다음 서비스를 시작합니다.

```bash
sudo install -o root -g root -m 0644 agent-app.service /etc/systemd/system/agent-app.service
sudo systemctl daemon-reload
sudo systemctl enable --now agent-app
sudo journalctl -u agent-app -b --no-pager
```

서비스 실행도 실제 앱 사용자는 `agent-admin`입니다. 서비스 실행 중에 터미널 앱을 추가로 띄우면 포트 충돌이 나므로 한 방식만 사용합니다. 서비스 종료는 `sudo systemctl stop agent-app`, 재시작은 `sudo systemctl restart agent-app`입니다.

### 4. 모니터링과 cron 등록

```bash
sudo -u agent-admin -H /home/agent-admin/agent-app/bin/monitor.sh
sudo systemctl enable --now cron
sudo -u agent-admin -H /home/agent-admin/agent-app/bin/install-cron.sh
sudo crontab -u agent-admin -l
```

로그는 `/var/log/agent-app/monitor.log`에 기록합니다. cron의 콘솔 출력과 오류는 `logger`를 통해 시스템 로그로 보냅니다.

```bash
sudo journalctl -t agent-monitor --since '10 minutes ago' --no-pager
sudo -u agent-admin tail -n 10 /var/log/agent-app/monitor.log
```

**자동 실행 확인**은 아래와 같이 전후 줄 수와 마지막 시각을 비교합니다. 기다리는 중에 `monitor.sh`나 `collect-evidence.sh`를 수동 실행하지 마세요. 수동 실행도 로그를 늘리므로 cron의 증거와 혼동할 수 있습니다.

```bash
sudo -u agent-admin wc -l /var/log/agent-app/monitor.log
sudo -u agent-admin tail -n 1 /var/log/agent-app/monitor.log
sleep 70
sudo -u agent-admin wc -l /var/log/agent-app/monitor.log
sudo -u agent-admin tail -n 2 /var/log/agent-app/monitor.log
sudo journalctl -t agent-monitor --since '3 minutes ago' --no-pager
```

### 5. 증거 및 통계 리포트

```bash
mkdir -p evidence
sudo bash collect-evidence.sh > evidence/system-current.txt 2>&1
sudo bash verify-permissions.sh > evidence/permissions-current.txt 2>&1
sudo journalctl -u agent-app -b --no-pager > evidence/boot-current.txt
sudo -u agent-admin /home/agent-admin/agent-app/bin/report.sh
```

선택 시간 범위는 시작과 끝 모두 포함합니다.

```bash
sudo -u agent-admin /home/agent-admin/agent-app/bin/report.sh \
  /var/log/agent-app/monitor.log '2026-09-05 00:00:00' '2026-09-05 23:59:59'
```

빈 파일/검색 결과 0건은 샘플 0개로 표시하며, 잘못된 행은 경고 후 제외합니다. 읽을 수 없는 파일이나 잘못된 날짜는 실패합니다. 기본 입력은 현재 `monitor.log` 한 개입니다.

## 설계와 요구사항 대응

- `AGENT_HOME=/home/agent-admin/agent-app`, `AGENT_PORT=15034` 등은 `agent-env.sh`에 고정하고 앱과 모니터가 같은 파일을 읽습니다. cron은 로그인 셸 설정에 의존하지 않습니다.
- `upload_files`는 `agent-common`, `api_keys`와 로그 디렉터리는 `agent-core`에 `rwx`를 주고 others 접근을 막습니다. setgid로 그룹을 물려주고 default ACL로 새 일반 파일에 그룹 쓰기 권한이 상속되게 합니다. 프로그램이 명시적으로 `chmod 600`을 하면 ACL도 제한될 수 있으므로 실제 접근 시험을 함께 수행합니다.
- `/home/agent-admin`은 공유 그룹에 **통과 권한만** ACL로 부여합니다. 이 상위 경로를 통과할 수 있어야 개발/테스트 계정이 하위 공유 디렉터리에 접근할 수 있습니다.
- `monitor.sh`는 소유자 `agent-dev`, 그룹 `agent-core`, `750`으로 설치합니다. 실행 계정은 `agent-admin`입니다.
- `/proc`의 실행 파일/스크립트 경로를 비교해 검색 명령 자체가 프로세스로 잘못 잡히는 일을 피합니다. 제공 바이너리와 `agent_app.py`를 지원합니다.
- 프로세스가 없거나 15034 리스너가 없거나 다른 프로세스의 리스너이면 종료 코드 1입니다. 앱과 모니터를 같은 사용자/기본 그룹으로 실행해야 `/proc`와 `ss`에서 PID를 확인할 수 있습니다. 서비스의 기본 그룹은 `agent-admin`, 보조 그룹은 `agent-common agent-core`로 지정했습니다.
- CPU는 1초 간격 `/proc/stat` 변화량, MEM은 `(MemTotal - MemAvailable) / MemTotal`, 디스크는 `df -P /`의 Used%입니다. 모두 앱 단독 사용량이 아닌 시스템 사용량입니다.
- CPU `>20`, MEM `>10`, DISK `>80`일 때 각각 경고합니다. 같은 값은 경고하지 않습니다. 방화벽이 꺼졌거나 상태를 읽을 수 없을 때도 경고 후 측정·로깅을 계속합니다.
- 비밀번호 없는 sudo는 **`agent-admin`의 `/usr/sbin/ufw status` 한 명령**에만 허용합니다. cron에서 비밀번호 입력을 기다리지 않게 하기 위한 읽기 전용 권한입니다.
- 로그 형식: `[YYYY-MM-DD HH:MM:SS] PID:... CPU:..% MEM:..% DISK_USED:..%`.
- 쓰기 직전에 10 MiB(10×1024×1024바이트)를 넘는지 확인해 순환합니다. `monitor.log` + `.1`~`.9`로 **현재 파일을 포함해 총 10개**를 유지하며 `.1`이 가장 최근 백업입니다. 자체 로직을 사용하므로 별도 logrotate 설정은 불필요합니다. `flock`으로 수동 실행과 cron의 중복 기록/회전을 막습니다.
- 선택 보너스 1은 구현했습니다. 선택 보너스 2인 7일 압축/30일 삭제는 구현 범위에 포함하지 않았습니다.

## 직접 설명할 핵심 개념

1. SSH 포트를 바꾸면 기본 포트를 겨냥한 잡음을 줄일 수 있지만 인증을 대체하지는 않습니다. root 원격 접속을 금지하면 개인 계정으로 로그인한 뒤 필요한 작업만 승격하게 됩니다.
2. 방화벽은 앱에 필요한 두 TCP 포트만 새 인바운드 연결에 열어 불필요한 접근을 줄입니다.
3. 세 역할은 업로드를 공유하지만 키와 운영 로그는 admin/dev만 접근합니다. 그룹과 ACL은 이 경계를 파일시스템에서 강제합니다.
4. 환경 변수를 명시하면 로그인 셸과 cron처럼 환경이 다른 실행 방식에서도 같은 경로/포트를 사용합니다.
5. 시각이 있는 로그가 쌓이면 장애 발생 시점의 자원 사용과 상태를 비교할 수 있습니다. 프로세스가 정상이라고 CPU/메모리가 항상 정상인 것은 아닙니다.
6. cron은 주기 실행을, 로그 순환은 디스크 사용량 제한을 담당합니다. 시간 기반 보존은 별도의 선택 정책입니다.

## 테스트

```bash
bash tests/run-tests.sh
```

테스트는 임시 디렉터리에만 합성 값을 기록하며 실제 계정·방화벽·cron을 변경하지 않습니다. 실서버 검증 결과는 별도의 `evidence/` 자료에 기록합니다.

## 참고한 공식 문서

- [Ubuntu 22.04 UFW 명령과 규칙](https://manpages.ubuntu.com/manpages/jammy/man8/ufw.8.html)
- [Ubuntu 22.04 sshd_config 설정과 Include](https://manpages.ubuntu.com/manpages/jammy/man5/sshd_config.5.html)
- [Linux /proc/stat CPU 카운터](https://www.man7.org/linux/man-pages/man5/proc_stat.5.html)

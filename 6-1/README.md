# AWS 웹 서비스 배포 실습

**서울 리전의 EC2에 Nginx를 배포하고, 외부 접속을 검증한 뒤 실습 리소스를 정리했다.**

실습일: **2026-10-07** · 검증 방식: **A — 브라우저 접속** · 현재 상태: **실습 리소스 정리 완료**

아래 순서로 구성 이유와 증거를 함께 설명한다. 캡처는 실습 당시의 원본이며, 서버는 삭제되어 현재 접속 시연은 불가능하다.

**바로 이동:** [목적](#1-무엇을-만들었는가) · [네트워크](#2-네트워크-구성) · [보안·IAM](#3-보안과-권한) · [접속 증거](#4-서버-실행과-외부-접속-검증) · [오류 해결](#5-실제-오류와-해결-과정) · [정리](#6-리소스-추적과-정리) · [추가 질문](#7-추가-질문에-대한-답변)

## 1. 무엇을 만들었는가?

> AWS에 Ubuntu 서버 한 대를 만들고 Nginx 웹 서버를 실행했습니다. 인터넷 연결과 접근 권한을 설정해 제 PC의 브라우저에서 웹페이지를 볼 수 있도록 했습니다.

AWS는 필요한 서버와 네트워크를 만들어 서비스를 운영할 수 있는 클라우드다. EC2가 실행 중이면 내 PC를 꺼도 서버는 계속 동작한다. 이번에는 서버 실행뿐 아니라 **인터넷 경로와 접근 제어**까지 직접 구성했다.

## 2. 네트워크 구성

### 구성 요소의 역할

| 구성 요소 | 역할 | 실제 설정 |
|---|---|---|
| **VPC** | AWS 안에서 논리적으로 분리한 내 네트워크 공간 | `mission-vpc`, `10.0.0.0/16` |
| **Public Subnet** | VPC 안의 작은 구역. IGW로 향하는 경로가 있음 | `mission-public`, `10.0.1.0/24` |
| **IGW** | VPC와 인터넷의 통신을 연결 | `mission-igw` |
| **Route Table** | 목적지에 따라 보낼 경로를 결정 | `0.0.0.0/0 → mission-igw` |
| **EC2** | Ubuntu와 Nginx를 실행한 가상 서버 | `mission-web`, `t3.micro` |
| **Nginx** | HTTP 요청을 받아 웹페이지를 응답 | Nginx 1.24.0 |

<img src="docs/architecture.png" alt="VPC, Public Subnet, IGW, EC2와 요청 흐름" width="760">

### 요청은 어떻게 도달하는가?

> 브라우저에서 서버의 퍼블릭 IP로 요청하면 인터넷과 IGW를 거쳐 Public Subnet의 EC2에 도달합니다. 보안 그룹에서 HTTP 요청이 허용되면 Nginx가 페이지를 응답합니다.

**외부 브라우저 → 인터넷 → IGW → Public Subnet의 EC2 → Nginx**

라우팅 테이블은 패킷이 방문하는 서버가 아니라 **경로를 정하는 규칙**이다. VPC 내부 목적지는 `10.0.0.0/16 → local`, 인터넷 목적지는 기본 경로 `0.0.0.0/0 → IGW`를 사용한다. 인터넷 통신에는 **IGW 연결·라우팅·퍼블릭 IP·접근 허용 설정**이 함께 필요하다. [AWS 인터넷 연결 설명](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html)

### localhost와 퍼블릭 IP의 차이

| 접속 위치와 주소 | 요청 대상 |
|---|---|
| 내 PC에서 `localhost` | 내 PC 자신 |
| EC2 터미널에서 `localhost` | EC2 자신 |
| 내 PC에서 `http://43.203.225.25` | 당시 해당 퍼블릭 IP를 사용한 EC2 |

주소 입력은 서버를 등록하는 행위가 아니다. 먼저 **EC2에 Nginx를 설치하고 외부 접속을 설정**했기 때문에 페이지가 표시됐다. 이번에는 도메인 연결 없이 퍼블릭 IP를 사용했다.

<details>
<summary>실제 리소스 이름과 ID 펼치기</summary>

| 항목 | 실제 값 |
|---|---|
| 리전 / 가용 영역 | `ap-northeast-2` / `ap-northeast-2a` |
| VPC | `vpc-02fb9f982bc0efd7c` |
| Subnet | `subnet-0afbc7e07dc484eb6` |
| IGW | `igw-0961d935789a435aa` |
| Route Table | `mission-public-rt`, `rtb-0168a69421d05e405` |
| EC2 | `i-0eea7fc0ae794a282` |
| 퍼블릭 / 프라이빗 IPv4 | `43.203.225.25` / `10.0.1.100` |
| Security Group | `mission-web-sg`, `sg-032fee0bca3d07fb8` |
| EBS | `vol-06042cc7766bda9e0`, `/dev/sda1`, 8GiB |
| 키페어 | `mission-key` |

</details>

## 3. 보안과 권한

### 필요한 인바운드 포트만 허용

| 용도 | 포트 | 허용 소스 | 이유 |
|---|---|---|---|
| 공개 웹페이지 | **HTTP 80** | `0.0.0.0/0` | 외부 브라우저 접속 허용 |
| 서버 관리 | **SSH 22** | `210.108.18.229/32` | 실습 PC의 공인 IP 한 개만 허용 |

> 웹페이지는 공개해야 해서 80을 전체 IPv4에 허용했습니다. SSH는 관리 기능이므로 제 IP에만 허용하고, 사용하지 않는 HTTPS·DB 포트는 추가하지 않았습니다.

`/32`는 단일 IPv4 주소다. 관리 포트를 불특정 주소에 열면 공격을 시도할 수 있는 범위가 커진다. DB를 추가한다면 Private Subnet에 배치하고, DB 포트는 애플리케이션 서버 보안 그룹에서만 접근하도록 검토한다. [AWS 보안 그룹 설명](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html)

**같은 `0.0.0.0/0`도 라우팅에서는 목적지 기본 경로, 인바운드에서는 모든 IPv4 소스를 의미한다.**

<details>
<summary>증거: EC2 생성 시 HTTP·SSH 인바운드 설정</summary>

![HTTP 80 공개 및 SSH 22의 내 IP 제한 설정](docs/security-group-rules.png)

</details>

### Security Group·IAM·루트의 차이

| 구분 | 관리하는 대상 | 실습 예 |
|---|---|---|
| **Security Group** | EC2의 네트워크 통신 | HTTP·SSH 포트와 소스 |
| **IAM** | 사용자·역할의 AWS 작업 권한 | `cloud-lab`의 EC2·VPC 작업 |
| **AWS 루트** | 계정 소유자의 강력한 권한과 루트 전용 작업 | 일상 작업에서 사용 최소화 |
| **Ubuntu 사용자** | EC2 내부 운영체제 작업 | `ubuntu`로 SSH 로그인 |

> 보안 그룹은 네트워크 접근을, IAM은 AWS 작업 권한을 제어합니다. 평소에는 필요한 권한만 가진 IAM을 사용해 실수와 계정 유출의 피해 범위를 줄입니다. Ubuntu의 sudo 권한은 AWS 루트 계정과 별개입니다.

`cloud-lab`에 연결한 [CloudLabSeoulPolicy](docs/iam-policy.json)는 필요한 EC2·VPC 작업을 명시하고, 생성·변경·삭제를 서울 리전으로 제한했다. 인스턴스 실행은 micro 유형으로 제한했으며 **AdministratorAccess와 S3·RDS 권한은 포함하지 않았다.**

**정책의 한계:** 조회용 `ec2:Describe*`에는 리전 제한이 없고 `Resource`가 `*`이므로 특정 실습 ID에만 접근하도록 제한한 정책은 아니다.

**계정 사용 기록:** 초기 계정 준비와 Billing 확인에 루트를 사용했다. 따라서 과제의 ‘IAM으로만 콘솔 접근’ 제약을 전 과정에서 준수했다고 설명할 수 없다. 후속 비용 조회를 필요한 읽기 권한을 가진 IAM으로 수행하는 것은 개선 방안이며 아직 적용·검증하지 않았다.

## 4. 서버 실행과 외부 접속 검증

> SSH로 EC2에 접속해 Nginx를 설치했습니다. 실행 상태와 서버 내부 응답을 확인하고, 외부 브라우저에서 페이지가 표시되는 것도 확인했습니다.

| 확인 항목 | 결과 | 의미 |
|---|---|---|
| EC2 상태 검사 | 실행 중, **3/3 통과** | 배포 당시 인스턴스 상태 확인 |
| SSH | `ubuntu@ip-10-0-1-100:~$` | 서버 로그인 확인 |
| Nginx 상태 | **active** | 웹 서버 실행 확인 |
| `curl -I http://localhost` | **HTTP/1.1 200 OK** | EC2 내부 웹 서버 응답 |
| `curl -I https://example.com` | **HTTP/2 200** | 서버의 인터넷 아웃바운드 |
| 외부 브라우저 | **Welcome to nginx!** | 외부에서 HTTP 접속 가능 |

**선택 방식: A — 브라우저 접속** · **검증 URL: `http://43.203.225.25`**

Nginx 기본 페이지로 웹 서버 배포를 확인할 수 있어 A를 선택했다. 서버 내부 검증과 외부 접속 검증을 각각 수행했다. B 방식의 `/health`는 구현하지 않았다.

![외부 브라우저 주소창과 Nginx 페이지](docs/external-access.png)

<details>
<summary>증거: SSH 로그인·Nginx active·HTTP 응답</summary>

2026-10-07 15:49에 저장한 캡처다. 내부 HTTP 응답 시각은 15:48:49 KST이다.

![서버 상태와 localhost 및 외부 HTTPS 요청 검증](docs/server-validation.png)

</details>

<details>
<summary>실제 설치·검증 명령 펼치기</summary>

SSH 접속 후 EC2의 Ubuntu 터미널에서 실행했다.

```bash
sudo apt update
sudo apt install -y nginx curl
sudo systemctl enable --now nginx
systemctl is-active nginx
curl -I http://localhost
curl -I https://example.com
```

</details>

## 5. 실제 오류와 해결 과정

> Ubuntu에 이미 접속한 상태에서 Windows용 SSH 명령을 다시 입력해 키 파일 경로 오류가 났습니다. 프롬프트와 오류 경로를 확인해 실행 환경이 다르다는 가설을 검증하고, 서버 작업을 이어갔습니다.

| 단계 | 실제 기록 |
|---|---|
| **증상** | Windows용 `$env:USERPROFILE` 경로의 키 파일을 찾지 못함 |
| **가설** | 현재 터미널이 Windows가 아니라 EC2의 Ubuntu 셸임 |
| **검증** | Ubuntu 프롬프트와 오류에 표시된 경로 확인 |
| **조치** | 추가 SSH 실행을 중단하고 접속된 서버에서 작업 진행 |
| **결과** | Nginx active, 내부·외부 HTTP 정상 응답, 브라우저 접속 성공 |
| **재발 방지** | Windows의 `PS ...>`와 Ubuntu 프롬프트를 구분 |

추측만으로 설정을 바꾸지 않고 **가설 → 증거 확인 → 조치 → 재검증** 순서로 진행했다. 근거는 오류 출력·프롬프트·서비스 상태·HTTP 응답이다. 이 사례에서 Nginx 로그 파일이나 CloudTrail을 조사했다는 기록은 없다.

<details>
<summary>증거: 실제 오류 화면</summary>

![Ubuntu에서 Windows용 SSH 명령을 실행한 오류](docs/ssh-environment-error.png)

</details>

Windows의 최초 SSH 명령 인식 실패까지 포함한 상세 기록은 [트러블슈팅 보고서](docs/troubleshooting.md)에 있다.

## 6. 리소스 추적과 정리

> `mission-` 이름 규칙과 리소스 ID로 실습 대상을 추적했습니다. 접속 증거와 연결된 디스크 ID를 보관한 뒤 EC2를 종료하고, 디스크·IP 잔여 여부와 네트워크 삭제를 확인했습니다.

| 필수 확인 대상 | 정리 결과 | 증거 |
|---|---|---|
| **EC2** | `mission-web` 종료됨 | [종료 화면](docs/cleanup-ec2-terminated.png) |
| **EBS** | 기록한 볼륨 ID 검색 결과 없음 | [볼륨 목록](docs/cleanup-ebs-absent.png) |
| **EIP** | 별도 할당 없음, 릴리스 대상 없음 | [IP 목록](docs/cleanup-eip-absent.png) |
| **IGW** | 실습 IGW 삭제 성공 | [삭제 상세](docs/cleanup-network-deleted.png) |
| **VPC** | `mission-vpc` 삭제 성공 | [삭제 화면](docs/cleanup-vpc-deleted.png) |

**정리 순서:** 증거 보관 → EC2 종료 → EBS·EIP 확인 → VPC와 연결된 네트워크 삭제 → 키페어 삭제 → Billing 확인

EC2를 먼저 종료해 연결된 네트워크 리소스를 정리할 수 있도록 했다. VPC 콘솔의 일괄 삭제로 서브넷·라우팅 테이블·보안 그룹·IGW를 함께 삭제했다. 확인한 항목만 완료로 표시했다.

<details>
<summary>증거: 네트워크 리소스 4개 삭제 성공</summary>

![보안 그룹·IGW·서브넷·라우팅 테이블 삭제 결과](docs/cleanup-network-deleted.png)

</details>

NAT Gateway·로드 밸런서·RDS 목록이 비어 있음을 사용자가 확인했으며 별도 캡처는 없다. 모든 리소스에 별도 Project 태그를 사용했다는 기록도 없다. 실제 추적 기준은 **이름·ID·리전·체크리스트**였다.

**비용 기록:** 2026-10-07 기준 계정 크레딧 잔액 **US$119.97**, 계정 누적 사용 **US$0.03**. 이번 실습 단독 비용으로 확정한 금액은 아니다. 당시 월별 비용 데이터는 준비 중이었으며, 새 비용 화면은 아직 기록하지 않았다.

전체 캡처와 확인 시각은 [리소스 정리 체크리스트](docs/cleanup-checklist.md)에 있다.

## 7. 추가 질문에 대한 답변

아래는 **대응 방안**이다. 실제로 해당 장애나 확장을 수행한 결과와 구분한다.

| 질문 | 설명할 핵심 |
|---|---|
| **외부 접속이 안 되면?** | **라우팅 → SG → 퍼블릭 IP/DNS → 서버·로그** 순서로 확인한다. localhost도 실패하면 서버 상태부터 해결한다. |
| **IAM 권한이 부족하면?** | 거부된 작업·대상·리전과 정책의 Action·Resource·Condition을 비교한다. 관리자 권한을 바로 주지 않고 필요한 범위만 수정한다. |
| **서버를 2대로 늘린다면?** | 부하 지표로 병목을 확인한 뒤 **ALB와 Target Group**으로 요청을 분산한다. 단일 서버 집중과 장애 지점을 줄이는 구성을 검토한다. |
| **예상치 못한 비용이 보이면?** | 청구서·Cost Explorer에서 **기간 → 서비스 → 리전 → 사용 유형**으로 좁힌다. 실습 이름·ID로 대상을 찾고 EC2·EBS·IP부터 확인한다. |

<details>
<summary>추가 설명: 진단 명령·확장 설계·비용 추적</summary>

**접속 장애:** 서브넷 Route Table의 기본 경로와 IGW 연결, 실제 EC2에 연결된 SG, 현재 퍼블릭 IP를 확인한다. 서버에서는 다음 명령으로 상태·응답·설정·로그를 조사할 수 있다. 이 명령 목록은 대응 예시다.

```bash
systemctl is-active nginx
curl -I http://localhost
sudo ss -lntp
sudo nginx -t
sudo journalctl -u nginx --no-pager -n 50
sudo tail -n 50 /var/log/nginx/error.log
```

**IAM 오류:** 권한 경계나 조직 정책의 명시적 거부도 확인한다. 인스턴스 종료가 거부됐다면 `ec2:TerminateInstances`와 대상·리전 조건부터 조사한다. [AWS 권한 거부 진단](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html)

**서버 확장:** 실제 부하 측정을 하지 않았으므로 CPU·메모리·네트워크 중 정확한 병목은 확정하지 않는다. 일반적인 리전 ALB에는 서로 다른 가용 영역의 서브넷 두 개 이상이 필요하므로 서브넷도 추가한다. 두 EC2를 Target Group에 등록하고 상태 확인을 설정한다. 서버 HTTP의 소스는 ALB 보안 그룹으로 제한하고, 공유할 세션·파일도 설계한다. [AWS ALB 설명](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html), [ALB 서브넷 요구사항](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/application-load-balancers.html)

**비용 추적:** 비용 내역에 따라 NAT Gateway·로드 밸런서·RDS·스냅샷·데이터 전송도 확인한다. 예상 비용·사용 비용·크레딧 적용 금액을 구분하고, 정리 후 데이터가 갱신되면 다시 비교한다. [AWS Cost Explorer 분석](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-exploring-data.html)

</details>

**보너스:** HTTPS·Docker는 수행하지 않았다. 외부 `https://example.com` 호출 성공은 내 서버에 HTTPS를 적용했다는 증거가 아니다.

## 8. 평가 항목과 제출 자료

| 평가 항목 | README에서 함께 볼 부분 |
|---|---|
| **항목 1 — 구성·동작·정리 확인** | 2~4절의 구성·접속 증거, 6절의 정리 표 |
| **항목 2 — 구성과 선택 이유** | 2절의 흐름, 3절의 포트 선택, 4절의 A 방식, 6절의 추적 기준 |
| **항목 3 — 원리 설명** | 기본 경로, SG와 IAM 차이, SSH IP 제한, 5절의 가설·검증 |
| **항목 4 — 상황별 대응** | 7절의 접속 장애·권한 오류·확장·비용 추적 |
| **항목 5 — 보너스** | 미수행으로 기록 |

17개 기본 질문과 보너스의 자세한 설명은 [평가 요소별 설명](docs/evaluation.md)에 있다.

<details>
<summary>제출 파일과 후속 확인 항목</summary>

| 파일 | 내용 |
|---|---|
| `docs/architecture.png` | 아키텍처 다이어그램 1장 |
| `docs/external-access.png` | 외부 브라우저 접속 증거 |
| `docs/server-validation.png` | 서버 상태·HTTP 응답 증거 |
| `docs/security-group-rules.png` | HTTP·SSH 인바운드 설정 증거 |
| `docs/iam-policy.json` | 실습 IAM 정책 |
| `docs/troubleshooting.md` | 실제 오류의 가설·검증·해결·재발 방지 |
| `docs/cleanup-checklist.md` 및 `docs/cleanup-*.png` | 정리 결과와 원본 증거 |
| `docs/evaluation.md` | 평가 요소별 상세 설명 |

- [x] 외부 접속·서버 검증·오류·보안 그룹 원본 캡처 보관.
- [x] 실습 리소스 정리 및 증거 기록.
- [x] NAT Gateway·로드 밸런서·RDS 목록 없음 사용자 확인.
- [x] Billing·크레딧 현황 기록.
- [ ] 월별 비용 데이터 준비 후 비용 금액 재확인.

EC2와 네트워크를 삭제했으므로 당시 URL은 현재 실습 서비스 접속 주소로 사용할 수 없다. 개인 키 PEM 파일은 제출 대상에서 제외했다.

</details>

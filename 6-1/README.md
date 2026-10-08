# AWS 웹 서비스 배포 실습

서울 리전의 VPC와 Public Subnet에 EC2 서버를 배치하고 Nginx 웹 서버를 실행했다. 2026년 10월 7일 외부 브라우저에서 `http://43.203.225.25`의 Nginx 기본 페이지가 표시되는 것을 확인했다. 서버 내부 응답과 인터넷 아웃바운드 통신도 검증했다.

현재 상태: **배포·접속 검증·실습 리소스 정리 완료**. EC2 종료, 실습 EBS·Elastic IP 잔여 없음 및 실습 VPC·서브넷·라우팅 테이블·보안 그룹·인터넷 게이트웨이·키페어 삭제를 확인했다. 증거는 [리소스 정리 체크리스트](docs/cleanup-checklist.md)에 첨부했다. 서울 리전의 NAT Gateway·로드 밸런서·RDS 데이터베이스 목록도 비어 있음을 사용자가 확인했다. Billing의 월별 비용 금액은 데이터 준비 후 재확인한다.

## 구성

| 항목 | 이름 또는 값 |
|---|---|
| 리전 | 서울 `ap-northeast-2` |
| 실습 IAM 사용자 | `cloud-lab` |
| VPC | `mission-vpc`, `10.0.0.0/16` |
| VPC ID | `vpc-02fb9f982bc0efd7c` |
| Public Subnet | `mission-public`, `10.0.1.0/24` |
| Subnet ID | `subnet-0afbc7e07dc484eb6` |
| 가용 영역 | `ap-northeast-2a` |
| Internet Gateway | `mission-igw`, `igw-0961d935789a435aa` |
| Route Table | `mission-public-rt`, `rtb-0168a69421d05e405` |
| 인터넷 경로 | `0.0.0.0/0 → mission-igw` |
| EC2 | `mission-web`, `i-0eea7fc0ae794a282`, `t3.micro` |
| OS / 웹 서버 | Ubuntu / Nginx 1.24.0 |
| 퍼블릭 IPv4 | `43.203.225.25` |
| 프라이빗 IPv4 | `10.0.1.100` |
| Security Group | `mission-web-sg`, `sg-032fee0bca3d07fb8` |
| 키페어 | `mission-key` |

![실습 아키텍처 다이어그램](docs/architecture.png)

## 네트워크 흐름과 접근 제어

외부 브라우저의 HTTP 요청은 EC2의 퍼블릭 IP를 통해 Internet Gateway를 거쳐 Public Subnet의 웹 서버에 도달한다. 서브넷은 `mission-public-rt`에 연결되어 있고, 외부로 나가는 IPv4 트래픽의 경로는 `0.0.0.0/0 → mission-igw`이다. VPC 내부 통신은 `10.0.0.0/16 → local` 경로를 사용한다.

| 인바운드 용도 | 프로토콜 / 포트 | 소스 |
|---|---|---|
| HTTP 웹 서비스 | TCP 80 | `0.0.0.0/0` |
| SSH 관리 | TCP 22 | 실습 시 내 공인 IP `210.108.18.229/32` |

Security Group은 서버로 들어오는 네트워크 트래픽을 제어한다. IAM은 AWS 리소스에 대한 생성·조회·수정·삭제 등의 API 권한을 제어한다.

## IAM 권한

사용자 생성 시 `CloudLabSeoulPolicy`를 연결했다. 정책 내용은 [iam-policy.json](docs/iam-policy.json)에 보관했다.

- EC2 관련 정보 조회: `ec2:Describe*`.
- VPC, 서브넷, Internet Gateway, 라우팅 테이블, 보안 그룹, 키페어, 태그 및 EC2 운영·정리에 필요한 작업을 명시적으로 허용.
- 생성·수정·삭제 요청 리전은 `ap-northeast-2`로 제한.
- `RunInstances`는 `t2.micro` 또는 `t3.micro`로 제한.
- 실습 정책에 `AdministratorAccess`, S3 및 RDS 권한을 포함하지 않음.

이 정책은 허용 작업과 리전을 제한한다. 리소스 ARN은 `*`이므로 실습 리소스 ID만으로 작업 대상을 제한하는 정책은 아니다. 정리 시 아래에 기록한 실습 리소스만 선택한다.

## 설치 및 검증

SSH 접속 후 Ubuntu 터미널에서 실행:

```bash
sudo apt update
sudo apt install -y nginx curl
sudo systemctl enable --now nginx
systemctl is-active nginx
curl -I http://localhost
curl -I https://example.com
```

| 검증 | 확인 결과 |
|---|---|
| EC2 상태 검사 | 실행 중, 3/3 검사 통과 |
| SSH 접속 | `ubuntu@ip-10-0-1-100:~$` 프롬프트 확인 |
| Nginx 실행 상태 | `active` |
| 서버 내부 HTTP | `HTTP/1.1 200 OK`, `Server: nginx/1.24.0 (Ubuntu)` |
| 인터넷 아웃바운드 | `https://example.com`에서 `HTTP/2 200` |
| 외부 브라우저 접속 | `Welcome to nginx!` 페이지 표시 |

서버 내부 검증 응답의 시각은 2026-10-07 06:48:49 GMT, 한국 시각 15:48:49이다.

외부 접속 검증 방식은 **A: 브라우저 접속**을 선택했다. 검증 URL은 `http://43.203.225.25`이다. HTTPS와 Docker 보너스 과제는 이번 실습 범위에 포함하지 않았다.

### 증거 1: 외부 브라우저 접속

2026-10-07 15:46에 저장한 원본 캡처다. 주소창의 `43.203.225.25`와 `Welcome to nginx!` 페이지가 함께 보여 외부 HTTP 접속 성공을 확인할 수 있다.

![외부 브라우저에서 EC2 퍼블릭 IP로 Nginx 페이지 접속 성공](docs/external-access.png)

### 증거 2: SSH 접속과 서버 검증

2026-10-07 15:49에 저장한 원본 캡처다. Ubuntu 로그인 프롬프트, Nginx의 `active`, localhost의 `HTTP/1.1 200 OK`, 외부 example.com의 `HTTP/2 200`을 확인할 수 있다.

![Ubuntu 터미널에서 Nginx 실행 및 내부 HTTP와 인터넷 아웃바운드 검증](docs/server-validation.png)

SSH 오류 당시 화면과 조치 후 결과는 [트러블슈팅 보고서](docs/troubleshooting.md)에 함께 첨부했다. 증빙 이미지는 원본 캡처를 수정하지 않고 보관했다.

## 평가 요소별 설명

첨부 평가표의 항목 1~5에 대한 설명은 [평가 요소별 설명 문서](docs/evaluation.md)에 정리했다. 필수 구성·SSH와 웹 서버·보안 그룹·외부 검증·정리 증거를 연결하고, 구성 이유와 네트워크·IAM 원리도 설명했다. 외부 접속 장애, IAM 권한 부족, 서버 2대 확장, 비용 추적은 실제 수행과 구분해 대응 방안으로 작성했다.

## 제출 파일

| 파일 | 내용 |
|---|---|
| `docs/architecture.png` | VPC, Subnet, IGW, EC2, SG와 요청 흐름 |
| `docs/external-access.png` | 주소창과 Nginx 페이지가 함께 보이는 사용자 캡처 |
| `docs/server-validation.png` | active, localhost 200, example.com 200이 보이는 사용자 캡처 |
| `docs/security-group-rules.png` | EC2 생성 시 HTTP 80 허용 및 SSH 22 특정 IP 제한 설정 캡처 |
| `docs/ssh-environment-error.png` | Ubuntu에서 Windows용 SSH 명령을 실행한 오류 캡처 |
| `docs/troubleshooting.md` | 실제 접속 오류의 분석·조치·결과 |
| `docs/cleanup-checklist.md` | 정리 대상, 수행 순서, 완료 근거 |
| `docs/evaluation.md` | 평가 항목 1~5의 설명 및 실제 증거·대응 방안 |

## 제출 확인 및 후속 확인

- [x] 브라우저 캡처를 `docs/external-access.png`로 저장하고 본문에 첨부.
- [x] Ubuntu 터미널 캡처를 `docs/server-validation.png`로 저장하고 본문에 첨부.
- [x] SSH 오류 캡처와 해결 후 증거를 트러블슈팅 보고서에 첨부.
- [x] 기록한 실습 리소스 정리 후 체크리스트에 확인 상태와 원본 캡처 기록.
- [x] 현재 상태에 배포·검증·기록한 실습 리소스 정리 완료 반영.
- [x] Billing 및 크레딧 현황 기록: 2026-10-07 16:36 KST, 잔여 US$119.97 / 계정 누적 사용 US$0.03. 이번 실습 단독 비용으로 확정하지 않음.
- [x] 서울 리전의 NAT Gateway·로드 밸런서·RDS 데이터베이스 목록이 비어 있음을 사용자 확인. 별도 캡처 없음.
- [ ] Billing 비용 데이터 준비 후 이번 달 비용 금액 재확인.

EC2 종료 및 네트워크 삭제 이후 검증 URL은 더 이상 실습 서비스에 접속하는 주소로 사용할 수 없다. 접속 성공은 저장한 캡처로 증명한다.

## 참고

- [AWS Internet Gateway와 인터넷 연결](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html)
- [AWS IAM 조건 연산자](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_condition_operators.html)
- [Ubuntu Nginx 설치](https://ubuntu.com/server/docs/how-to-install-nginx/)
- [AWS VPC 삭제](https://docs.aws.amazon.com/vpc/latest/userguide/delete-vpc.html)

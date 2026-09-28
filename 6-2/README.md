# AI 커밋 / PR 초안 생성기

평가표 항목 1~4의 질문별 답변, 설계 이유, 시연 순서 및 증빙 범위는 [평가항목 설명](평가항목_설명.md)에 정리했습니다. 보너스는 제외합니다.

## Codyssey 연결 및 Windows 실행

제공된 Codyssey 문서 기준 설정입니다. API 키를 설정한 같은 PowerShell 창에서 실행하세요.

```powershell
$env:AI_API_URL = 'https://copa.codyssey.kr/v1/chat/completions'
$env:AI_MODEL = 'gemini-3-flash'
cd C:\Users\user\Desktop\2026\codessey
py -3.12 .\6-2\main.py commit --path 6-2
py -3.12 .\6-2\main.py pr --path 6-2
```

`--path 6-2`는 다른 미션 변경을 제외합니다. 생략하면 저장소 전체를 수집합니다.
이 PC의 MSYS2 `python`에서 TLS 인증서 검증 실패가 재현되어, 정상적으로 HTTPS에 연결되는 `py -3.12` 사용을 권장합니다. 인증서 검증을 비활성화하지 않습니다. 사용자 실제 실행으로 커밋 초안과 PR 본문 생성까지 확인했습니다.

Git 변경 사항을 AI API에 전달하여 한국어 커밋 메시지 또는 PR 초안을 터미널에 출력하는 Python CLI입니다. 추가미션은 포함하지 않습니다.

## 설치 및 실행 위치

Python 3.10 이상과 Git이 필요합니다. Python 표준 라이브러리만 사용하므로 별도 패키지 설치는 필요 없습니다.

이 프로젝트는 상위 `codessey` Git 저장소의 `6-2` 폴더에 있습니다. **Git 저장소 루트인 `codessey`에서 실행하세요.** 수집 범위는 해당 저장소 전체의 staged/unstaged 변경입니다. 다른 미션 변경이 섞여 있는지 먼저 확인하세요.

```powershell
cd C:\Users\user\Desktop\2026\codessey
git status
py -3.12 .\6-2\main.py --help
```

신규 파일은 `git diff`에 나타나지 않습니다. 내용을 분석하려면 필요한 파일을 먼저 `git add` 하세요. 스테이징은 커밋을 만들지 않습니다. `.env`와 API 키가 들어 있는 파일은 추가하지 마세요.

## 자체 API 설정

현재 연결부는 다음 계약을 사용하는 **Chat Completions 호환 API**입니다. Codyssey 문서 및 사용자 실제 실행으로 호환성을 확인했습니다. 다른 API의 규격이 다르면 `main.py`의 `call_api()`를 수정해야 합니다.

- POST 요청, HTTPS 전체 URL을 `AI_API_URL`로 지정
- 인증 헤더: `Authorization: Bearer <AI_API_KEY>`
- 요청 JSON: `model`, `messages`, `temperature`, `max_tokens`
- 응답 텍스트: `choices[0].message.content`
- 모델이 JSON 출력 지시를 따르고 지정한 파라미터를 지원해야 함

PowerShell에서 URL과 모델을 실제 서비스 값으로 바꾸세요. 아래 URL과 모델은 예시용 자리표시자입니다.

```powershell
$env:AI_API_URL = 'https://your-api.example/v1/chat/completions'
$env:AI_MODEL = 'your-model-name'
# 키를 화면이나 명령 기록에 직접 남기지 않고 입력
$secret = Read-Host 'API Key' -AsSecureString
$env:AI_API_KEY = [System.Net.NetworkCredential]::new('', $secret).Password
Remove-Variable secret
```

키는 환경변수로만 읽습니다. `.env` 파일 자동 로딩은 하지 않습니다. 키를 코드, README, 채팅 또는 Git에 저장하지 마세요.

## 사용 예시

저장소 루트에서 실행합니다.

```powershell
py -3.12 .\6-2\main.py commit --path 6-2
py -3.12 .\6-2\main.py pr --path 6-2
py -3.12 .\6-2\main.py commit --path 6-2 --temperature 0.2 --max-tokens 4096
py -3.12 .\6-2\main.py pr --path 6-2 --safe-mode
```

- `--model`: 기본값 `AI_MODEL`
- `--temperature`: 기본값 0.2, 허용 범위 0~2. 낮을수록 비교적 일관된 표현을 유도합니다. 실제 지원 범위는 API에 따라 다릅니다.
- `--max-tokens`: 기본값 4096. 출력 토큰 한도이며 너무 작으면 응답이 잘릴 수 있습니다. 실제 실행에서 1200으로 잘린 응답이 4096에서 정상 생성되어 기본값을 조정했습니다.
- `--safe-mode`: 기본 활성화. `--no-safe-mode`로 해제할 수 있습니다.

변경 사항이 없으면 API를 호출하지 않고 종료합니다. 새로운 파일만 있고 스테이징하지 않았다면 `git add` 안내와 함께 종료합니다. API 키 누락, 인증 실패, 네트워크 오류, 형식 오류는 오류 메시지와 종료 코드 1로 알립니다.

## 출력 예시

아래는 설명용 예시이며 실제 API로 생성한 결과는 아닙니다.

```text
--- Commit Message ---
feat: Git 변경 기반 커밋 초안 생성 추가

- Git 변경 수집 및 API 응답 처리 구현
----------------------
```

```text
--- PR Title ---
feat: 커밋 및 PR 초안 생성 도구 추가

--- PR Body ---

## Why
- 변경 사항 설명을 작성하는 반복 작업을 줄이기 위한 것으로 추정됩니다.

## What
- Git 변경 수집과 AI 기반 초안 생성 명령을 추가했습니다.

## How to Test
- 변경 파일을 스테이징하고 commit 및 pr 명령의 출력 형식을 확인하세요.
```

커밋 제목은 50자 이내를 권장하도록 요청하고, 최대 72자로 후처리합니다. PR 제목은 최대 80자로 후처리합니다. 제목의 줄바꿈은 제거하며, PR은 Why / What / How to Test에 각각 1개 이상 불릿이 있는지 검증합니다. 잘못된 JSON이나 누락된 PR 항목은 내용 조작 없이 오류로 처리합니다. 커밋 본문은 선택이며 생성되면 불릿으로 표시합니다.

## 보안 및 비용

기본 안전 모드는 이메일, 일부 API 키 패턴, api_key / secret / password 등 대입 형태를 마스킹하고 diff를 최대 200줄로 제한합니다. 파일 목록은 최대 100줄, 전체 입력은 최대 60,000자로 제한합니다. 현재 사용 중인 API 키는 안전 모드와 무관하게 입력에서 제거합니다.

마스킹이 모든 비밀정보를 탐지하지는 못합니다. 전송 전 `git diff` 및 `git diff --cached`로 확인하세요. `.gitignore`는 이미 추적 중인 민감 파일을 보호하지 않습니다. 생략된 diff는 요약 정확도를 낮출 수 있습니다. 안전 모드 고도화나 사용자 지정 규칙은 추가미션이므로 구현하지 않았습니다.

각 명령은 API를 최대 1회 호출하고 호출 횟수를 stderr에 기록합니다. 자동 재시도나 재생성은 하지 않습니다. 다시 실행하면 추가 비용이 발생할 수 있습니다. HTTPS 리다이렉트는 인증 헤더 전달을 방지하기 위해 따르지 않습니다.

실제 적용한 모델·temperature·max_tokens도 stderr에 기록해 비교 실험을 확인할 수 있습니다. 안전 모드나 입력 크기 제한으로 내용을 생략하면 경고를 출력합니다.

출력은 검토용 초안입니다. 프로그램은 커밋, push, 실제 GitHub PR 생성을 수행하지 않습니다. 배경 추정과 테스트 제안이 사실에 맞는지 검토한 뒤 사용하세요.

## 테스트

```powershell
cd .\6-2
py -3.12 -m unittest -v
```

테스트는 임시 Git 저장소 및 모의 API 응답을 사용하며 유료 API를 호출하지 않습니다. staged/unstaged 수집, 변경 없음, 신규 파일 안내, 마스킹, 제목 제한, PR 필수 항목, API 요청 및 인증 오류를 확인합니다.

## 검증 결과

- 자동 테스트 16개 통과: Git 수집 및 경로 필터링, 마스킹, 출력 형식, API 인증/인증서 오류 처리, 키 누락, 토큰 잘림, 잘못된 응답 구조, Git 수집부터 터미널 출력까지의 모의 API 통합 검증 등
- 사용자 실제 실행: Codyssey `gemini-3-flash`, `--path 6-2`, `--max-tokens 4096`으로 커밋 초안 및 PR 본문 생성 성공
- 실제 커밋 제목: `AI 커밋/PR 생성기 구현 및 경로 필터링 기능 추가`
- 실제 PR 본문에서 Why / What / How to Test와 각 섹션의 불릿 확인
- 안전 모드에서 diff가 200줄로 제한되므로 전체 변경에 대한 설명이 빠질 수 있음. 초안을 실제 변경과 비교하고 보완할 것

## 과제 요구사항과 구현 대응

| 요구사항 | 구현 |
| --- | --- |
| Git 변경 수집 | collect_changes: git status 및 staged/unstaged git diff |
| AI REST API 연동 | call_api: POST 요청, Bearer 인증, JSON 응답 처리 |
| 실행 옵션 | 모델, temperature, max-tokens, safe-mode, path |
| 커밋 / PR 초안 | commit / pr 명령과 목적별 프롬프트 |
| 형식 검증 | 제목 길이 후처리, PR 필수 섹션 및 불릿 검사 |
| 오류 처리 | 변경 없음, 키 누락, HTTP 오류, TLS, DNS, 타임아웃 |
| 기본 안전 모드 | 패턴 마스킹 및 전송량 제한 |
| 문서화 | 설치, 환경변수, 실행, 출력 예시, 보안 및 비용 |

핵심 흐름은 `Git 변경 → 입력 정리 → AI 요청 → 응답 검증 → 사람의 검토`입니다. 프롬프트로 원하는 내용을 요청하고 프로그램으로 결과 형식을 검증합니다. 도구 자체는 커밋하거나 push하지 않으며, 제출 시 개발자가 소스 파일을 GitHub에 올립니다. 실제 PR 작성, 팀 컨벤션 커스터마이징, 안전 모드 고도화는 추가미션이므로 제외했습니다.

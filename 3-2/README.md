# Mini Git

**커밋 그래프와 역색인을 직접 구현한 Python CLI 프로그램**

브랜치를 만들고 커밋 이력을 기록하면서 위상 정렬, BFS, DFS, 병합 정렬, 역색인의 동작을 확인할 수 있습니다.

| 실행 환경 | 설치 | 데이터 저장 | 구현 범위 |
| --- | --- | --- | --- |
| Python 3.10 이상 | 외부 패키지 불필요 | 메모리 — 종료 시 삭제 | 필수 과제만 구현 |

```powershell
python main.py
```

> **범위:** 보너스인 `diff`, 브랜치 `merge`, 정렬 성능 비교는 제외했습니다. 병합 정렬(merge sort)은 필수 정렬 알고리즘이며 브랜치 병합과는 별개입니다.

### 바로 찾아보기

| 목적 | 읽을 내용 |
| --- | --- |
| 처음 실행하기 | [실행 환경](#setup) → [간단한 실행 예시](#quick-example) |
| 명령 확인하기 | [명령어 목록](#commands) · [동작 규칙과 오류](#behavior) |
| 코드 이해하기 | [자료구조와 알고리즘](#implementation) · [시간·공간 복잡도](#complexity) |
| 평가 준비하기 | [전체 시연](#demo) · [평가 질문 20개와 답변](#evaluation) |
| 제출 전 확인하기 | [테스트](#tests) · [요구사항 대응표](#requirements) |

<a id="setup"></a>

## 1. 실행 환경과 파일 구성

- Python **3.10 이상**
- 외부 패키지 설치 불필요: Python 표준 라이브러리만 사용합니다.
- 운영체제: Python 실행이 가능한 Windows, macOS, Linux

```text
3-2/
├── main.py         # 필수 제출물: 프로그램과 REPL 진입점
├── README.md       # 필수 제출물: 사용법과 구현 설명
└── test_main.py    # 추가 검증용 자동 테스트
```

프로그램 실행에는 `main.py` 하나면 충분합니다. 두 필수 제출물은 `main.py`와 `README.md`이며 테스트 파일은 검증용입니다.

프로젝트 폴더에서 다음 명령을 실행합니다.

```powershell
python --version
python main.py
```

Windows에서 `python` 대신 Python 런처를 사용하는 환경이라면 `py -3 main.py`로 실행할 수 있습니다. 실행한 인터프리터의 버전이 3.10 이상인지 확인하세요.

```text
Mini Git | INIT <user_name>으로 시작하세요. exit / quit로 종료합니다.
mini-git>
```

`mini-git>` 뒤에 명령을 입력합니다. `exit`, `quit`, EOF 또는 `Ctrl+C`로 종료합니다. 프로그램을 종료하면 저장소 데이터가 사라지며, 다음 실행은 빈 저장소에서 시작합니다.

<a id="commands"></a>

## 2. 명령 문법

- 명령 이름은 대소문자를 구분하지 않습니다. `INIT`, `init`, `Init`이 같습니다.
- 사용자명·메시지·검색어 등에 공백이 있으면 전체를 따옴표로 감쌉니다.
- 작은따옴표와 큰따옴표를 모두 사용할 수 있습니다.
- 옵션 이름과 옵션 값은 아래 표기 그대로 소문자로 입력합니다.
- 브랜치 이름과 작성자 이름은 대소문자를 구분합니다.
- 빈 문자열이나 공백만 있는 인자는 허용하지 않습니다.
- 커밋 hash는 출력된 **전체 값**을 입력해야 합니다. 축약 hash는 지원하지 않습니다.

**저장소와 브랜치 관리**

| 명령 | 기능 | 예시 |
| --- | --- | --- |
| `INIT <user_name>` | 저장소, `main` 브랜치, 작성자 초기화 | `init "Alice Kim"` |
| `BRANCH <branch_name>` | 현재 HEAD를 가리키는 브랜치 생성 | `branch feature` |
| `SWITCH <branch_name>` | 현재 브랜치 전환 | `switch feature` |
| `COMMIT <message>` | 현재 HEAD를 부모로 새 커밋 생성 | `commit "Add login feature"` |

**로그와 그래프 탐색**

| 명령 | 기능 | 예시 |
| --- | --- | --- |
| `LOG` | 저장소 전체를 부모가 먼저 나오도록 출력 | `log` |
| `LOG --sort-by=date` | timestamp 오름차순 출력 | `log --sort-by=date` |
| `LOG --sort-by=author` | 작성자 이름 오름차순 출력 | `log --sort-by=author` |
| `PATH <commit1> <commit2>` | 양방향 연결에서 최단 경로 출력 | `path 00000002 00000003` |
| `ANCESTORS <commit_hash>` | 자신을 제외한 모든 조상 출력 | `ancestors 00000003` |

**검색과 종료**

| 명령 | 기능 | 예시 |
| --- | --- | --- |
| `SEARCH <keyword>` | 메시지 토큰 역색인 검색 | `search "LOGIN"` |
| `SEARCH --author=<name>` | 작성자 역색인 검색 | `search --author="Alice Kim"` |
| `exit` / `quit` | 종료 | `quit` |

예를 들어 큰따옴표를 메시지에 포함하려면 `commit 'Say "hello"'`처럼 바깥에 작은따옴표를 사용합니다. 파서는 `shlex.split()`이며, 따옴표를 닫지 않으면 `Invalid args`를 출력합니다.

<a id="quick-example"></a>

## 3. 처음부터 실행해 보기

새로 실행한 프로그램에서 다음 순서대로 입력합니다. 아래 hash는 증가 카운터로 생성되므로 첫 실행의 입력 순서와 동일하게 재현됩니다.

```text
mini-git> init "Alice Kim"
Initialized repository.
Current branch: main
Current user: Alice Kim
mini-git> commit "Initial commit"
[main 00000001] Initial commit
mini-git> branch feature
Created branch: feature
mini-git> switch feature
Switched to branch: feature
mini-git> commit "Add login feature"
[feature 00000002] Add login feature
mini-git> switch main
Switched to branch: main
mini-git> commit "Add payment feature"
[main 00000003] Add payment feature
mini-git> path 00000002 00000003
00000002->00000001->00000003
mini-git> quit
Bye.
```

이때 관계는 다음과 같습니다. 화살표는 자식에서 부모로 향합니다.

```text
00000002 (feature) ──> 00000001 <── 00000003 (main, 현재 HEAD)
```

종료 전에 아래 명령도 실행해 볼 수 있습니다.

```text
log
log --sort-by=date
log --sort-by=author
ancestors 00000003
search login
search "add feature"
search --author="Alice Kim"
path 00000003 00000003
```

- `log`: `00000001`, `00000002`, `00000003` 순서로 세 커밋을 표시합니다.
- `ancestors 00000003`: `00000001`의 메타데이터만 표시합니다.
- `search login`: `00000002`만 표시합니다.
- `search "add feature"`: 두 토큰을 모두 가진 `00000002`, `00000003`을 표시합니다.
- 작성자 검색: Alice Kim이 만든 세 커밋을 표시합니다.
- 자신으로 향하는 경로: 간선 수가 0이므로 `00000003`만 표시합니다.

로그·검색·조상 출력은 공통 형식을 사용합니다. 실제 timestamp는 커밋을 생성한 UTC 시각입니다.

```text
commit 00000002 | author: Alice Kim | timestamp: 2026-09-08T09:00:00.123456+00:00
    Add login feature
```

<a id="behavior"></a>

## 4. 세부 동작과 선택한 규칙

### 초기화, 브랜치, HEAD

`INIT`은 최초 한 번만 허용합니다. 다시 실행하면 `Repository already initialized`를 출력하고 기존 데이터를 보존합니다. 이 프로그램의 명령에는 작성자 변경 기능이 없으므로, 한 REPL 세션에서 만든 커밋은 같은 작성자를 갖습니다. 작성자 정렬과 역색인 로직 자체는 여러 작성자도 처리하며, 자동 테스트에서 별도 노드로 검증합니다.

브랜치는 커밋을 복사하지 않고 마지막 커밋 hash를 보관합니다. `BRANCH`는 브랜치만 생성하고 자동으로 전환하지 않습니다. `SWITCH` 후 커밋하면 전환한 브랜치의 포인터만 이동합니다.

커밋이 없을 때 HEAD는 `None`입니다. 이때 브랜치를 생성할 수도 있습니다. 서로 다른 빈 브랜치에서 각각 첫 커밋을 만들면 부모가 없는 독립 루트가 생기므로 두 커밋 사이에는 경로가 없습니다.

별도로 새 프로그램을 실행해 다음 예시를 확인할 수 있습니다.

```text
init Alice
branch empty
commit "Root A"
switch empty
commit "Root B"
path 00000001 00000002
```

마지막 출력은 `No path`입니다.

### 로그와 정렬

`LOG`는 **현재 브랜치뿐 아니라 저장소 전체**를 출력합니다. Kahn 위상 정렬로 모든 부모가 자식보다 먼저 나오도록 보장합니다. 여러 커밋이 동시에 출력 가능한 경우 저장소 등록 순서와 FIFO 큐 순서로 결정합니다.

옵션 로그는 위상 정렬 대신 지정한 키로 전체 커밋을 정렬합니다.

- `date`: UTC timestamp 오름차순, 즉 오래된 시각부터 출력합니다.
- `author`: Python 문자열 비교 기준의 오름차순입니다. 언어별 사전 정렬이나 대소문자 통합 정렬은 아닙니다.
- 키가 같으면 안정 정렬에 따라 **커밋 등록 순서**를 유지합니다.
- 옵션 로그는 부모 우선 순서를 별도로 보장하지 않습니다. 부모 우선 출력은 옵션 없는 `LOG`의 규칙입니다.

### 메시지 검색

메시지를 `message.lower().split()`으로 토큰화합니다. 검색어에도 동일한 규칙을 적용하고 역색인에서 후보를 가져옵니다.

- `LOGIN`과 `login`은 같은 키워드입니다.
- 완전한 토큰 기준입니다. `login` 검색은 `logging`을 찾지 않습니다.
- 구두점은 제거하지 않습니다. `bug,`와 `bug`는 다른 토큰입니다.
- 공백을 포함한 검색어는 **모든 토큰을 포함하는 AND 검색**으로 정의했습니다. `search "add login"`은 `add`와 `login`이 모두 있는 커밋을 찾습니다. 연속된 문구 일치 검색은 아닙니다.
- 메시지에 같은 단어가 여러 번 있어도 결과 커밋은 한 번만 나옵니다.
- 작성자 검색은 공백과 대소문자를 포함한 이름 전체의 정확한 일치를 사용합니다.
- 검색 결과와 조상 목록은 hash 문자열 오름차순으로 표시합니다.

### 오류와 빈 결과

오류가 발생해도 REPL은 종료되지 않고 다음 명령을 받습니다.

| 상황 | 출력 |
| --- | --- |
| 초기화 전에 저장소 명령 실행 | `Repository not initialized` |
| 다시 초기화 | `Repository already initialized` |
| 인자 개수, 따옴표, 옵션 형식 오류 | `Invalid args` |
| 존재하지 않는 명령 | `Unknown command: <command>` |
| 같은 브랜치 이름 재사용 | `Branch already exists: <name>` |
| 없는 브랜치로 전환 | `Unknown branch: <name>` |
| 없는 커밋으로 탐색 | `Unknown commit: <hash>` |
| 커밋 없는 저장소의 로그 | `No commits` |
| 일치하는 검색 결과 없음 | `No matches` |
| 부모가 없는 커밋의 조상 조회 | `No ancestors` |
| 존재하는 두 커밋 사이에 연결 없음 | `No path` |

빈 줄은 무시합니다. `PATH`는 두 hash의 존재부터 검증하므로 잘못된 hash 입력은 `No path`가 아니라 `Unknown commit` 오류입니다.

<a id="implementation"></a>

## 5. 자료구조와 코드 설명

### 커밋 노드와 저장소

`Commit`은 불변 dataclass이며 다음 필드를 갖습니다.

| 필드 | 타입 | 의미 |
| --- | --- | --- |
| `hash` | `str` | 세션에서 유일한 커밋 식별자 |
| `message` | `str` | 커밋 메시지 |
| `author` | `str` | 생성 시점의 작성자 |
| `timestamp` | `datetime` | 시간대 정보가 있는 UTC 생성 시각 |
| `parents` | `tuple[str, ...]` | 부모 커밋 hash 목록 |

`MiniGit`의 주요 상태는 다음과 같습니다.

| 속성 | 구조 | 역할 |
| --- | --- | --- |
| `commits` | `dict[hash, Commit]` | hash로 평균 O(1)에 노드 조회 |
| `branches` | `dict[name, hash 또는 None]` | 브랜치별 마지막 커밋 |
| `current_branch` | 문자열 | 현재 선택한 브랜치 |
| `head` | 계산된 속성 | 현재 브랜치의 마지막 커밋 |
| `neighbors` | `dict[hash, set[hash]]` | PATH를 위한 부모·자식 양방향 인접 목록 |
| `index` | `InvertedIndex` | 메시지 및 작성자 역색인 |
| `counter` | 정수 | 중복 없는 식별자 생성 |

hash는 증가하는 정수를 최소 8자리 16진수로 표현합니다. 예: `00000001`, `00000002`, …, `0000000a`. 암호학적 해시가 아니라 과제에서 허용한 카운터 기반 식별자입니다. 자리수를 초과해도 문자열을 잘라내지 않으며, 재초기화와 카운터 초기화를 허용하지 않으므로 세션 내 중복이 없습니다.

### DAG가 유지되는 이유

새 커밋은 이미 존재하는 현재 HEAD만 부모로 가리킵니다. 기존 커밋의 부모 관계는 수정하지 않습니다. 따라서 자식에서 부모로 간선을 따라가면 생성 순서상 이전 커밋으로만 이동하므로 사이클이 생기지 않습니다.

`parents` 자료형과 탐색 함수는 여러 부모를 표현·탐색할 수 있습니다. 다만 필수 CLI에서 생성되는 커밋은 부모가 0개 또는 1개이며, 다중 부모 커밋을 만드는 병합 명령은 제공하지 않습니다. `neighbors`의 양방향 연결은 PATH 탐색을 위한 별도 표현이므로 원래 커밋 DAG의 방향성은 유지됩니다.

### 부모 우선 로그: `topological_order()`

1. 각 커밋의 부모 수를 진입 차수로 기록하고 부모에서 자식으로 향하는 목록을 만듭니다.
2. 부모가 없는 커밋을 큐에 넣습니다.
3. 큐에서 커밋을 꺼내 출력 목록에 추가합니다.
4. 해당 커밋의 자식들의 남은 부모 수를 줄입니다.
5. 모든 부모 처리가 끝난 자식만 큐에 넣습니다.

단순한 날짜 정렬은 시계 변경이나 동일 시각 때문에 부모 우선을 보장하지 못하지만, 이 방식은 부모 관계 자체를 사용합니다. 처리한 노드 수가 전체보다 작으면 사이클이 있는 잘못된 그래프로 판단합니다.

### 최단 경로: `shortest_path()`

커밋과 부모의 연결을 무방향 간선으로 취급합니다. 목적지에서 BFS를 실행해 각 커밋의 목적지까지의 최소 간선 수를 계산합니다. 출발지가 거리 표에 없으면 `No path`입니다.

경로 복원 시에는 현재 거리보다 정확히 1 작은 이웃만 후보로 선택합니다. 이 후보들은 모두 최단 경로를 완성할 수 있으므로, 다음 hash와 `->` 구분자를 포함한 문자열이 가장 작은 후보를 고르면 전체 최단 경로 문자열도 사전순 최소가 됩니다. `set`의 순회 순서에 결과가 좌우되지 않습니다.

필수 명령만으로 만든 그래프에서는 연결된 두 커밋 사이의 경로가 유일합니다. 동률 처리도 요구사항에 있으므로 함수에 구현하고, 테스트용 그래프에서 복수 최단 경로를 검증합니다.

### 조상 탐색: `ancestor_hashes()`

스택을 사용하는 반복형 DFS로 부모 방향만 탐색합니다. 방문 집합으로 중복을 막고 시작 커밋 자신은 제외합니다. 재귀를 사용하지 않아 커밋 이력이 길어도 Python 재귀 깊이 제한에 걸리지 않습니다. 출력 직전에 결과만 hash 기준으로 정렬합니다.

### 직접 구현한 정렬: `merge_sort()`

상향식 병합 정렬 하나를 구현했습니다. 길이 1인 정렬 구간에서 시작하여 길이 2, 4, 8, … 순으로 인접 구간을 병합합니다. `key` 함수로 날짜·작성자·hash 비교 기준을 바꿉니다.

두 원소의 키가 같으면 왼쪽 원소를 먼저 선택하므로 **안정 정렬**입니다. 입력 목록은 변경하지 않고 새 목록을 반환합니다. `sorted()`, `list.sort()` 및 표준 정렬 관련 API를 사용하지 않습니다. 코드의 `min()`은 가장 작은 후보 하나를 고르는 연산이며 목록을 정렬하지 않습니다.

### 역색인: `InvertedIndex`

예를 들어 메시지 `Add login feature`가 있는 커밋을 만들면 다음 관계가 추가됩니다.

```text
keywords["add"]     -> {해당 hash, ...}
keywords["login"]   -> {해당 hash, ...}
keywords["feature"] -> {해당 hash, ...}
authors["Alice Kim"] -> {해당 hash, ...}
```

검색은 해당 키의 후보 집합을 직접 조회하며 전체 `commits`를 순회하지 않습니다. 여러 토큰은 가장 작은 후보 집합부터 교집합을 구합니다. 후보 hash에 해당하는 커밋만 가져와 출력용 정렬을 수행합니다.

<a id="complexity"></a>

## 6. 시간·공간 복잡도

`V`는 전체 커밋 수, `E`는 부모 간선 수, `L`은 메시지 길이, `K`는 검색 결과 수, `A`와 `E_A`는 도달 가능한 조상 수와 관련 간선 수입니다. 아래는 문자열 비교·해시 계산 비용을 별도로 제외한 일반적인 자료구조 분석입니다. 해시맵과 집합 연산은 평균적인 경우를 기준으로 합니다.

| 기능 | 시간 복잡도 | 추가 공간 | 설명 |
| --- | --- | --- | --- |
| 커밋 hash 조회 | 평균 O(1) | O(1) | 해시맵 조회 |
| 브랜치 생성·전환 | 평균 O(1) | 생성 시 O(1) | 포인터 관리 |
| 커밋 생성·색인 | O(L) | O(L) 이내 | 메시지 토큰화 및 색인 추가, 필수 CLI의 부모 수는 최대 1 |
| 기본 LOG | O(V + E) | O(V + E) | Kahn 위상 정렬 |
| 옵션 LOG | O(V log V) | O(V) | 병합 정렬 |
| PATH | O(V + E) | O(V) | 목적지 BFS와 거리 감소 경로 복원 |
| 조상 탐색 | O(A + E_A) | O(A + E_A) | 스택 및 방문 집합 |
| ANCESTORS 출력까지 | O(A + E_A + A log A) | O(A + E_A) | 조상 결과 정렬 포함 |
| 단일 토큰·작성자 검색 | 평균 O(1 + K) | O(K) | 색인 조회 후 결과 집합 복사 |
| 검색 출력까지 | O(1 + K + K log K) | O(K) | 결과만 병합 정렬 |

여러 검색 토큰이 `Q`개이고 가장 작은 후보 집합 크기가 `M`이면, 교집합 처리는 평균 O(Q × M) 상한으로 볼 수 있습니다. 여기에 검색어 토큰화와 결과 정렬·출력 비용이 더해집니다. 검색 결과가 전체 커밋과 같으면 그만큼의 출력 비용은 피할 수 없습니다.

병합 정렬은 최선·평균·최악 모두 O(N log N) 시간, O(N) 보조 공간을 사용합니다. 재귀 호출은 없습니다. 역색인은 전체 메시지를 매번 확인하는 선형 검색과 달리, 미리 저장한 토큰별 후보만 확인하는 대신 색인을 위한 추가 메모리를 사용합니다. 프로그램 전체 저장 공간은 커밋 메타데이터, 브랜치 포인터, 그래프 간선, 토큰·작성자별 색인 항목 수에 비례합니다.

<a id="tests"></a>

## 7. 테스트 실행

```powershell
python -m unittest -v
```

외부 테스트 프레임워크는 필요하지 않습니다. `test_main.py`는 다음 항목을 검증합니다.

- 초기화, 명령 대소문자 처리, 따옴표와 공백 인자
- 브랜치 분기 후 서로 다른 HEAD와 부모 관계
- 전체 로그의 부모 우선 순서
- 경로의 양방향 탐색, 연결 없는 경우, 자기 자신으로의 경로
- 복수 최단 경로의 문자열 사전순 동률 처리
- 공유 조상 중복 제거 및 1,500개 커밋의 반복형 탐색
- 키워드·작성자 역색인, AND 검색, 구두점 및 대소문자 규칙
- 병합 정렬의 빈 입력, 홀수 길이, 중복 키, 안정성
- 날짜·작성자 정렬 및 동률 시 등록 순서 유지
- 잘못된 명령·인자 입력 후 저장소 상태 보존
- 보너스 `diff`, `merge` 명령이 제공되지 않음

여러 부모나 여러 작성자가 있는 테스트 데이터는 알고리즘 검증용으로만 구성합니다. 실제 CLI에 병합이나 작성자 변경 기능을 추가한 것은 아닙니다.

<a id="requirements"></a>

## 8. 과제 요구사항 대응 및 범위

| 필수 요구사항 | 구현 위치 |
| --- | --- |
| REPL, 대소문자와 따옴표 처리, 오류 처리 | `main()`, `MiniGit.execute()` |
| INIT / BRANCH / SWITCH / COMMIT | `MiniGit` |
| 필수 커밋 필드 및 유일 hash | `Commit`, `MiniGit.create_commit()` |
| 부모 우선 LOG | `topological_order()` |
| 날짜·작성자 정렬, 직접 구현 정렬 | `merge_sort()` 및 LOG 옵션 분기 |
| 무방향 최단 경로와 사전순 동률 처리 | `shortest_path()` |
| 모든 조상 탐색 | `ancestor_hashes()` |
| 메시지·작성자 역색인 | `InvertedIndex` |
| 실행 진입점 및 상세 문서 | `main.py`, `README.md` |

이 프로그램은 파일 내용이나 변경 내역을 저장하지 않습니다. 실제 Git 저장소 및 `.git` 폴더를 조작하지 않으며, 네트워크 통신과 파일 기반 영속 저장도 없습니다. 모든 처리는 실행 중인 프로그램의 메모리 안에서 이루어집니다.

<a id="demo"></a>

## 9. 평가 시연용 실행 예시와 실제 출력

아래 예시는 `main.py`의 REPL을 실행하고 명령 입력을 자동 공급하여 수집한 출력입니다. 평가할 때는 새로 `python main.py`를 실행하고 다음 명령을 순서대로 입력하면 됩니다. hash는 같은 입력 순서에서 재현되며 timestamp는 실행 시각에 따라 달라집니다. `mini-git>`는 프롬프트이므로 직접 입력하지 않습니다.

### 9.1. 복사해서 사용할 명령

```text
init "Alice Kim"
branch isolated
commit "Initial commit"
branch feature
switch feature
commit "Add login feature"
commit "Fix login bug"
switch main
commit "Add payment feature"
log
path 00000003 00000004
path 00000001 00000003
path 00000003 00000003
ancestors 00000003
search LOGIN
search "add feature"
search --author="Alice Kim"
log --sort-by=date
log --sort-by=author
switch isolated
commit "Independent root"
path 00000001 00000005
ancestors 00000005
search missing
switch missing
path 00000001 unknown
commit too many words
switch main
quit
```

### 9.2. 실제 실행 결과

<details>
<summary><strong>전체 실행 로그 펼치기 — 명령 29개와 실제 출력</strong></summary>

```text
Mini Git | INIT <user_name>으로 시작하세요. exit / quit로 종료합니다.
mini-git> init "Alice Kim"
Initialized repository.
Current branch: main
Current user: Alice Kim
mini-git> branch isolated
Created branch: isolated
mini-git> commit "Initial commit"
[main 00000001] Initial commit
mini-git> branch feature
Created branch: feature
mini-git> switch feature
Switched to branch: feature
mini-git> commit "Add login feature"
[feature 00000002] Add login feature
mini-git> commit "Fix login bug"
[feature 00000003] Fix login bug
mini-git> switch main
Switched to branch: main
mini-git> commit "Add payment feature"
[main 00000004] Add payment feature
mini-git> log
commit 00000001 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Initial commit
commit 00000002 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Add login feature
commit 00000004 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Add payment feature
commit 00000003 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Fix login bug
mini-git> path 00000003 00000004
00000003->00000002->00000001->00000004
mini-git> path 00000001 00000003
00000001->00000002->00000003
mini-git> path 00000003 00000003
00000003
mini-git> ancestors 00000003
commit 00000001 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Initial commit
commit 00000002 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Add login feature
mini-git> search LOGIN
commit 00000002 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Add login feature
commit 00000003 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Fix login bug
mini-git> search "add feature"
commit 00000002 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Add login feature
commit 00000004 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Add payment feature
mini-git> search --author="Alice Kim"
commit 00000001 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Initial commit
commit 00000002 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Add login feature
commit 00000003 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Fix login bug
commit 00000004 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Add payment feature
mini-git> log --sort-by=date
commit 00000001 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Initial commit
commit 00000002 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Add login feature
commit 00000003 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Fix login bug
commit 00000004 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Add payment feature
mini-git> log --sort-by=author
commit 00000001 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Initial commit
commit 00000002 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Add login feature
commit 00000003 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Fix login bug
commit 00000004 | author: Alice Kim | timestamp: 2026-09-08T09:21:24.317095+00:00
    Add payment feature
mini-git> switch isolated
Switched to branch: isolated
mini-git> commit "Independent root"
[isolated 00000005] Independent root
mini-git> path 00000001 00000005
No path
mini-git> ancestors 00000005
No ancestors
mini-git> search missing
No matches
mini-git> switch missing
Unknown branch: missing
mini-git> path 00000001 unknown
Unknown commit: unknown
mini-git> commit too many words
Invalid args
mini-git> switch main
Switched to branch: main
mini-git> quit
Bye.
```

</details>

### 9.3. 시연에서 확인할 평가 포인트

| 확인 대상 | 기대 결과와 의미 |
| --- | --- |
| 초기화 | `main` 브랜치와 `Alice Kim` 사용자가 설정되고 첫 커밋 전 HEAD는 `None` |
| 브랜치 반영 | `feature`에는 `00000003`, `main`에는 `00000004`가 남음 |
| 부모 우선 로그 | `00000001`은 `00000002`, `00000004`보다 먼저, `00000002`는 `00000003`보다 먼저 출력 |
| 위상 정렬과 날짜 정렬의 차이 | 기본 로그는 큐 순서상 `01, 02, 04, 03`, 날짜 정렬은 이 실행에서 `01, 02, 03, 04` |
| 양방향 최단 경로 | `03->02->01->04`: 공통 조상까지 올라간 뒤 다른 브랜치의 자식으로 내려감 |
| 자기 자신 경로 | `path 00000003 00000003`은 hash 하나만 출력 |
| 여러 조상 | `ancestors 00000003`은 `00000001`, `00000002`를 출력하고 자신은 제외 |
| 키워드 검색 | `LOGIN`은 소문자로 정규화되어 `00000002`, `00000003` 검색 |
| 공백 검색어 | `"add feature"`는 두 토큰을 모두 갖는 `00000002`, `00000004` 검색 |
| 작성자 검색·정렬 | 해당 시점의 네 커밋 모두 검색되며, 작성자가 같아 작성자 정렬은 등록 순서 유지 |
| 경로 없음 | 빈 상태에서 미리 만든 `isolated`의 첫 커밋은 독립 루트이므로 `01`과 `05` 사이에 `No path` |
| 오류 복구 | 잘못된 브랜치·hash·인자 오류 뒤에도 `switch main`과 `quit`이 정상 실행 |

표의 `01` 같은 표기는 설명용 축약이며 실제 입력에는 `00000001`처럼 전체 hash를 사용합니다. 서로 다른 작성자에 대한 정렬은 CLI에 작성자 변경 기능이 없으므로 `test_sort_options`에서 별도 데이터로 검증합니다.

<a id="evaluation"></a>

## 10. 평가 요소별 답변

`e3-2 mini git.pdf` 10~11쪽의 **5. 평가문항**에 대응합니다. **질문을 클릭하면 답변이 펼쳐집니다.**

| 평가 항목 | 질문 수 | 핵심 내용 |
| --- | --- | --- |
| 1. 기능 동작 | 6개 | 초기화, 브랜치, 로그, 경로, 조상, 검색·정렬 |
| 2. 코드 설계 | 5개 | 상태 분리, hash, 색인 갱신, 함수 재사용, 주석 |
| 3. 알고리즘 이해 | 5개 | DAG, 위상 정렬, BFS, 안정 정렬, 역색인 |
| 4. 변경 대응 | 4개 | 규모 증가, 간선 방향, 정렬 조건, hash 생성 방식 |

> 항목 1~3은 현재 구현에 대한 설명입니다. 항목 4는 요구사항이 바뀔 때의 설계 제안이며 추가 구현한 기능은 아닙니다.

### 항목 1. 필수 기능 동작

<details>
<summary><strong>1-1. INIT 후 main 브랜치, HEAD, 현재 사용자가 초기화되는가?</strong></summary>

**답변:** `MiniGit.initialize()`에서 현재 사용자를 저장하고 `branches["main"] = None`으로 초기 브랜치를 만듭니다. `current_branch`의 초기값은 `main`이며, `head` 속성은 현재 브랜치의 값을 조회합니다. 따라서 초기화 직후에는 `main`을 선택한 상태이고 커밋이 없으므로 HEAD는 `None`입니다.

첫 커밋을 만들면 main과 HEAD가 그 hash를 가리킵니다. 다시 INIT을 실행하면 기존 데이터를 지우지 않고 오류를 반환합니다.

**코드 참고:** `MiniGit.__init__()`, `head`, `initialize()`, `create_commit()` · 확인: `test_initialization_and_case_insensitive_commands`

</details>

<details>
<summary><strong>1-2. BRANCH 생성, SWITCH 전환, 해당 브랜치의 COMMIT 반영이 되는가?</strong></summary>

**답변:** `BRANCH`는 현재 HEAD의 hash를 새 브랜치 이름에 연결하고, `SWITCH`는 `current_branch`를 변경합니다. `COMMIT`은 전환한 브랜치의 기존 HEAD를 부모로 저장한 뒤 그 브랜치의 포인터만 새 hash로 바꿉니다. 다른 브랜치의 포인터는 그대로 유지되므로 각 브랜치에서 독립적으로 작업할 수 있습니다.

**코드 참고:** `MiniGit.execute()`의 `BRANCH`·`SWITCH`·`COMMIT`, `create_commit()` · 확인: `test_branch_divergence_and_log`

</details>

<details>
<summary><strong>1-3. LOG가 부모를 자식보다 먼저 출력하는가?</strong></summary>

**답변:** 옵션 없는 `LOG`는 `topological_order()`의 Kahn 알고리즘을 사용합니다. 각 커밋의 아직 처리하지 않은 부모 수를 세고, 이 수가 0인 커밋만 출력 큐에 넣습니다. 따라서 모든 부모가 출력된 뒤에만 자식이 출력됩니다. 현재 브랜치뿐 아니라 저장소 전체를 대상으로 합니다.

**코드 참고:** `topological_order()`, `MiniGit.execute()`의 `LOG` · 확인: `test_branch_divergence_and_log`

</details>

<details>
<summary><strong>1-4. PATH가 최단 경로 또는 No path를 출력하는가?</strong></summary>

**답변:** 커밋과 부모의 연결을 양방향으로 저장하고, 목적지에서 BFS를 수행하여 최소 간선 수를 구합니다. 출발점에서 목적지까지 거리가 1씩 줄어드는 이웃을 따라가면 최단 경로가 됩니다. 여러 후보가 있으면 `hash1->hash2->...` 경로 문자열의 사전순이 가장 작은 결과를 선택합니다. 두 커밋이 모두 존재하지만 연결되지 않았을 때 `No path`를 출력합니다.

**코드 참고:** `shortest_path()`, `create_commit()`의 `neighbors`, `execute()`의 `PATH` · 확인: `test_shortest_path_lexicographic_tie`

</details>

<details>
<summary><strong>1-5. ANCESTORS가 모든 조상을 빠짐없이 출력하는가?</strong></summary>

**답변:** `ancestor_hashes()`에서 시작 커밋의 부모들을 스택에 넣고 반복형 DFS를 수행합니다. 방문한 각 노드의 부모도 계속 스택에 넣으므로 직접 부모뿐 아니라 그 위의 모든 조상까지 탐색합니다. 방문 집합으로 중복을 제거하고 시작 커밋 자체는 제외합니다.

**코드 참고:** `ancestor_hashes()`, `MiniGit.execute()`의 `ANCESTORS` · 확인: `test_topological_order_and_shared_ancestors`

</details>

<details>
<summary><strong>1-6. 키워드·작성자 검색과 날짜·작성자 정렬이 동작하는가?</strong></summary>

**답변:** 키워드 검색은 메시지를 소문자·공백 기준 토큰으로 색인한 `keywords`를, 작성자 검색은 이름 전체를 키로 저장한 `authors`를 조회합니다. 전체 커밋을 순회하지 않고 일치하는 hash만 가져옵니다. 날짜·작성자 정렬은 직접 구현한 `merge_sort()`에 각각 timestamp와 author를 비교 키로 전달하며, 오름차순으로 출력합니다. 동률이면 등록 순서를 유지합니다.

**코드 참고:** `InvertedIndex`, `merge_sort()`, `MiniGit.execute()`의 `SEARCH`·옵션 `LOG` · 확인: `test_sort_options`

</details>

### 항목 2. 코드 구조와 설계 설명

<details>
<summary><strong>2-1. 저장소·브랜치·HEAD·사용자 정보를 어떻게 분리했는가?</strong></summary>

**답변:** 커밋 본문은 `commits: dict[hash, Commit]`, 브랜치 포인터는 `branches: dict[name, hash 또는 None]`, 선택된 브랜치는 `current_branch`, 현재 사용자는 `user`로 나눴습니다. HEAD는 별도 복사본을 저장하지 않고 `branches[current_branch]`에서 계산하는 속성입니다.

이렇게 하면 브랜치 포인터와 HEAD를 따로 갱신하다가 서로 어긋나는 문제를 줄일 수 있습니다. 검색 데이터는 `InvertedIndex`, 경로 탐색용 양방향 관계는 `neighbors`로 분리했습니다.

**코드 참고:** `MiniGit.__init__()`, `head`, `Commit`, `InvertedIndex`

</details>

<details>
<summary><strong>2-2. hash 조회 구조와 중복·충돌 방지 방법은 무엇인가?</strong></summary>

**답변:** Python `dict`에서 커밋 hash를 키, `Commit` 객체를 값으로 사용하여 평균 O(1)에 조회합니다. 커밋 식별자는 증가 카운터를 16진수 문자열로 변환하므로 같은 세션에서 같은 식별자를 다시 만들지 않습니다. 8자리를 넘어도 값을 잘라내지 않고, 재초기화도 거부합니다.

여기서 **커밋 식별자가 같은 문제**와 **dict 내부 해시 충돌**은 다릅니다. 전자는 카운터로 예방하고, 후자는 Python dict가 키 동등성 검사와 내부 충돌 처리로 구분합니다. 따라서 서로 다른 문자열의 내부 해시가 충돌해도 같은 커밋으로 덮어쓰는 것은 아닙니다. 현재 식별자는 암호학적 해시가 아닙니다.

**코드 참고:** `MiniGit.__init__()`의 `commits`·`counter`, `create_commit()`

</details>

<details>
<summary><strong>2-3. 커밋 추가 시 역색인은 언제, 어떻게 갱신하는가?</strong></summary>

**답변:** `create_commit()`에서 노드를 생성하고 저장소·인접 목록·현재 브랜치를 갱신한 뒤, 반환하기 전에 `self.index.add(commit)`을 호출합니다. `add()`는 `message.lower().split()` 결과를 집합으로 중복 제거하고, 각 토큰의 hash 집합과 작성자의 hash 집합에 새 hash를 추가합니다.

따라서 COMMIT 명령이 정상 종료된 직후부터 새 커밋을 검색할 수 있습니다. 현재는 단일 프로세스의 순차 REPL이며, 동시 쓰기나 영속 저장을 위한 트랜잭션까지 구현한 것은 아닙니다.

**코드 참고:** `MiniGit.create_commit()`, `InvertedIndex.add()`·`search()`

</details>

<details>
<summary><strong>2-4. LOG·PATH·ANCESTORS의 탐색 로직은 어떻게 재사용하는가?</strong></summary>

**답변:** 각각 `topological_order(commits)`, `shortest_path(neighbors, start, end)`, `ancestor_hashes(commits, start)`라는 독립 함수로 구현했습니다. 함수는 입력 자료구조를 받아 목록·집합·경로를 반환하며 직접 사용자 입력을 받거나 출력하지 않습니다. `MiniGit.execute()`는 명령 파싱과 존재 검증 후 이 함수들을 호출하고, `format_commits()`는 공통 출력 형식을 담당합니다.

덕분에 REPL 없이 작은 그래프만 넣어 알고리즘을 테스트할 수 있습니다. 서로 다른 탐색을 하나의 함수로 억지로 합치기보다, 각 알고리즘을 독립적으로 재사용하도록 구성했습니다.

**코드 참고:** `topological_order()`, `shortest_path()`, `ancestor_hashes()`, `format_commits()`

</details>

<details>
<summary><strong>2-5. docstring과 주석은 어떤 기준으로 작성했는가?</strong></summary>

**답변:** 주요 클래스와 함수의 docstring에는 역할, 입력·반환의 의미 또는 핵심 동작 규칙을 적었습니다. 예를 들어 `ancestor_hashes()`에는 반복형 DFS와 자신 제외 규칙을, `merge_sort()`에는 비교 키와 안정성을 설명했습니다. 주석은 코드만으로 의도가 바로 드러나지 않는 부분에 작성했습니다.

역색인에서 작은 후보 집합부터 교집합을 계산하는 이유와, PATH 동률 비교에서 구분자를 포함하는 이유가 그 예입니다. 전체 처리 과정과 시간복잡도는 README에서 보충합니다.

**코드 참고:** `main.py` 모듈 상단과 각 클래스·함수 선언 바로 아래의 `"""..."""`

</details>

### 항목 3. 자료구조·알고리즘 이해

<details>
<summary><strong>3-1. 커밋 그래프가 왜 DAG여야 하며 사이클이 있으면 어떤 문제가 생기는가?</strong></summary>

**답변:** 커밋은 이전 이력을 부모로 참조합니다. 부모 관계를 계속 따라가다가 자신으로 돌아오면 자기 자신의 과거가 되는 모순이 생깁니다. 또한 사이클 안에서는 모든 부모를 자식보다 먼저 출력하는 순서를 만들 수 없고, 방문 검사 없는 탐색은 무한 반복할 수 있습니다.

현재 구현은 새 커밋에서 기존 HEAD로만 간선을 추가하고 기존 노드를 불변으로 유지해 사이클을 예방합니다. Kahn 알고리즘은 전체 노드를 처리하지 못하면 `Invalid commit graph`를 발생시킵니다. 조상 탐색의 방문 집합은 중복 방문을 막지만, 방문 집합이 있다는 것만으로 잘못된 그래프가 정상적인 커밋 이력이 되는 것은 아닙니다.

**코드 참고:** `MiniGit.create_commit()`, `topological_order()`, `ancestor_hashes()`

</details>

<details>
<summary><strong>3-2. LOG의 부모 우선 조건은 어떤 접근으로 만족시켰는가?</strong></summary>

**답변:** Kahn 위상 정렬을 적용했습니다. 저장된 간선은 자식에서 부모로 향하지만, 출력 계산에서는 부모에서 자식으로 향하는 임시 목록을 만들고 각 커밋의 부모 수를 진입 차수로 사용합니다. 부모 없는 노드부터 FIFO 큐로 처리하고, 자식의 남은 부모 수가 0이 될 때만 큐에 넣습니다.

각 노드와 간선을 한 번씩 처리하므로 O(V + E) 시간입니다. 단순 timestamp 정렬은 시각이 같거나 시스템 시간이 바뀌면 부모 우선을 보장하지 못합니다.

**코드 참고:** `topological_order()`, `MiniGit.execute()`의 옵션 없는 `LOG`

</details>

<details>
<summary><strong>3-3. PATH에서 BFS를 선택한 이유와 무방향 간선을 사용하는 이유는 무엇인가?</strong></summary>

**답변:** 모든 간선의 비용이 1이고 최소 간선 수가 목적이므로 BFS가 적합합니다. DFS는 먼저 발견한 경로가 최단이라는 보장이 없습니다. BFS는 가까운 거리부터 방문하여 O(V + E)에 최단 거리를 계산합니다.

무방향 연결은 과제에서 정한 PATH의 정의입니다. 다른 브랜치 사이를 이동하려면 한 커밋에서 공통 조상으로 올라간 뒤 다른 자식으로 내려가는 것도 허용해야 합니다. 커밋 DAG 자체의 부모 방향을 없앤 것이 아니라, PATH 전용 `neighbors`에서만 부모·자식 양쪽을 이웃으로 보관했습니다. 목적지 기준 거리 계산 뒤 사전순으로 경로를 복원하여 동률 규칙도 만족시킵니다.

**코드 참고:** `shortest_path()`, `MiniGit.create_commit()`의 `neighbors`

</details>

<details>
<summary><strong>3-4. 정렬 알고리즘의 평균·최악 시간복잡도와 안정성은 무엇인가?</strong></summary>

**답변:** 상향식 병합 정렬을 직접 구현했습니다. 각 단계에서 전체 N개 원소를 병합하고 구간 길이를 두 배로 늘리므로 단계 수가 약 log₂N입니다. 최선·평균·최악 시간복잡도는 모두 O(N log N), 보조 공간은 O(N)입니다. 재귀는 사용하지 않습니다.

키가 같을 때 왼쪽 구간의 원소를 먼저 선택하는 `<=` 비교를 사용하므로 안정 정렬입니다. 날짜나 작성자가 같으면 기존 등록 순서가 보존됩니다. `key` 함수만 바꿔 여러 정렬 기준에 재사용하며 `sorted()`나 `list.sort()`는 사용하지 않습니다.

**코드 참고:** `merge_sort()`, `MiniGit.execute()`의 옵션 `LOG`

</details>

<details>
<summary><strong>3-5. 역색인이 순회 검색보다 빠른 이유는 무엇인가?</strong></summary>

**답변:** 순회 검색은 요청할 때마다 V개 커밋의 메시지를 확인해야 하므로 메시지 길이를 일정하다고 보아도 O(V)입니다. 역색인은 커밋 생성 시 `keyword -> hash 집합`, `author -> hash 집합`을 미리 만들어 두므로 검색 때 해시맵으로 해당 후보만 가져옵니다.

일치 결과가 K개라면 단일 키 조회와 후보 복사는 평균 O(1 + K)이고, 현재 프로그램은 출력 정렬까지 포함하면 O(1 + K + K log K)입니다.

검색 결과가 전체에 가까우면 출력 비용이 커서 항상 큰 차이가 나는 것은 아닙니다. 또한 빠른 검색 대신 색인 저장 메모리와 커밋 생성 시 토큰화 비용을 추가로 사용합니다. 여러 토큰 검색은 후보 집합의 교집합으로 처리합니다.

**코드 참고:** `InvertedIndex.add()`·`search()`, `MiniGit.create_commit()`

</details>

### 항목 4. 규모 증가와 요구사항 변경에 대한 대응

<details>
<summary><strong>4-1. 커밋 수가 10배 늘면 병목은 어디이며 어떻게 개선할 수 있는가?</strong></summary>

**답변:** 커밋마다 부모가 최대 1개인 현재 구조에서 E도 V에 비례한다고 보면, 전체 LOG·PATH 탐색과 저장 메모리는 대체로 선형으로 증가합니다. 옵션 로그는 O(V log V)이므로 기존 대비 증가율이 `10 × log(10V) / log(V)`여서 단순 10배보다 큽니다.

검색 결과가 많은 키워드는 후보 복사와 결과 정렬·출력이 병목이 될 수 있습니다. `format_commits()`가 전체 문자열을 조립하는 비용과 터미널 출력량도 고려해야 합니다.

**개선 방향:** 다음은 현재 구현에 추가하지 않은 설계 제안입니다.

- 부모→자식 인접 목록을 생성 시 함께 유지하여 매 LOG마다 목록을 다시 만드는 비용을 줄입니다. 전체 로그를 출력하는 한 O(V + E) 자체가 사라지지는 않습니다.
- 부모가 최대 1개인 현재 구조를 유지한다면 루트·깊이 정보를 저장하고 두 노드를 부모 방향으로 올려 공통 조상을 찾을 수 있습니다. 이 경우 전체 연결 요소 BFS 대신 두 경로 길이에 비례한 탐색이 가능합니다. 다중 부모 DAG로 확장되면 이 전략을 그대로 적용할 수 없습니다.
- 반복되는 정렬 결과를 캐시하고 새 커밋 생성 시 무효화합니다. 변경 없이 같은 정렬을 반복하는 경우의 비용을 줄일 수 있습니다.
- 결과를 순차적으로 출력하면 거대한 출력 문자열을 한꺼번에 보관하는 메모리를 줄일 수 있습니다. 페이지 단위 출력은 인터페이스 요구사항 변경을 전제로 고려합니다.
- 역색인이 커지면 압축된 정수 ID나 비트맵 같은 표현을 검토할 수 있습니다. 집합 연산 속도, 추가 구현 비용, 메모리 사용을 함께 비교해야 합니다.

**코드 참고:** `topological_order()`, `shortest_path()`, `merge_sort()`, `InvertedIndex`, `format_commits()`

</details>

<details>
<summary><strong>4-2. PATH를 부모 방향만 허용하도록 바꾸면 결과와 구현은 어떻게 달라지는가?</strong></summary>

**답변:** 출발 커밋에서 조상으로 올라가는 경로만 허용됩니다. 9절의 `00000003->00000002->00000001`은 가능하지만, 루트 `00000001`에서 자식 `00000003`으로 가는 경로는 없어집니다. 서로 다른 브랜치 끝인 `00000003`과 `00000004` 사이도 공통 조상에서 자식으로 내려갈 수 없으므로 `No path`가 됩니다. 자기 자신으로의 경로는 그대로 유효합니다.

구현을 단순하게 바꾸려면 출발지에서 BFS를 시작하고 이웃을 `commits[current].parents`로 제한하면 됩니다. 최단 경로 동률 규칙도 그대로 유지해야 합니다.

**현재의 목적지 기준 거리 계산 방식을 유지한다면 주의가 필요합니다.** 목적지 BFS는 원래 방향을 뒤집은 부모→자식 간선을 따라야 하고, 출발지에서 경로를 복원할 때는 원래의 자식→부모 간선만 따라야 합니다. 현재 `neighbors`를 단순히 부모 목록으로 교체하면서 목적지 BFS를 그대로 두면 도달 방향을 반대로 계산하게 됩니다.

**코드 참고:** `shortest_path()`, `MiniGit.create_commit()`의 `parents`·`neighbors`

</details>

<details>
<summary><strong>4-3. 작성자 정렬에도 부모·자식 선후를 유지하라는 조건이 추가되면 어떻게 해결하는가?</strong></summary>

**답변:** 전체 커밋을 author로 먼저 정렬하면 부모보다 자식이 앞설 수 있습니다. Kahn 위상 정렬을 유지하되, 현재 부모 처리가 끝난 **출력 가능한 커밋들 중에서** 작성자 이름이 가장 작은 것을 선택하겠습니다. 동률 기준은 등록 순서 등으로 명시합니다.

과제의 표준 정렬 API 금지를 유지하려면 직접 만든 최소 힙에 `(author, 등록 순번, hash)`를 넣는 전략이 가능합니다. 삽입·삭제가 O(log V)이므로 전체 시간은 O(E + V log V)입니다.

설명이 더 단순한 대안으로는 후보 목록에서 매번 직접 최솟값을 찾을 수 있지만, 최악 O(V² + E)이므로 규모가 크면 불리합니다. 이는 변경 요구에 대한 설명이며 현재 코드에는 힙이나 추가 정렬 알고리즘을 구현하지 않았습니다.

두 조건이 충돌할 수 있다는 점도 명확히 해야 합니다. 예를 들어 부모 작성자가 Zoe이고 자식이 Alice이면 전역적인 이름 오름차순과 부모 우선은 동시에 불가능합니다. 따라서 **부모 우선은 반드시 지키고, 현재 출력 가능한 후보 사이에서 작성자 순서를 적용한다**는 해석을 요구자와 합의해야 합니다.

**코드 참고:** 현재 `topological_order()`와 `merge_sort()`의 선택 기준을 비교

</details>

<details>
<summary><strong>4-4. 카운터 기반과 난수 기반 hash가 테스트·재현성·디버깅에 미치는 영향은 무엇인가?</strong></summary>

**답변:** 카운터 방식은 새 세션에서 같은 순서로 명령을 실행하면 같은 hash를 얻습니다. 예상 출력 작성과 버그 재현이 쉽고 생성 순서를 추적하기도 좋습니다. 한 세션에서 카운터를 되돌리지 않으면 중복이 없지만, 서로 다른 세션에서는 같은 값이 생길 수 있습니다. 현재 과제의 보장 범위는 세션 내부이므로 적합합니다.

난수 방식은 실행마다 값이 달라질 수 있어 서로 다른 환경에서 식별자 공간을 공유하기에는 유리하지만, 난수만으로 충돌이 절대 없다고 보장할 수는 없습니다. 새 후보가 `commits`에 있는지 검사하고 중복이면 다시 생성해야 기존 커밋을 덮어쓰지 않습니다. 유한한 식별자 공간이 소진되거나 난수기가 같은 값만 내는 경우에도 무한 재시도하지 않도록 실패 처리 정책이 필요합니다.

테스트에서는 생성기를 주입하거나 테스트 전용 고정 시드로 결과를 재현하고, 같은 후보가 연속 생성되는 충돌 상황도 검사하겠습니다. 일반 기능 테스트는 특정 hash 상수보다 생성 결과에서 받은 hash를 연결하여 검사하는 편이 좋습니다.

디버깅 로그에는 생성된 hash와 부모 관계를 남겨야 합니다. 또한 hash 문자열이 바뀌면 복수 최단 경로 중 사전순으로 선택되는 경로도 달라질 수 있으므로, 동률 테스트는 통제된 hash로 구성해야 합니다.

**코드 참고:** `MiniGit.create_commit()`, `Commit`, `shortest_path()`

</details>

### 항목 5. 보너스 과제

**미수행.** `diff`, 브랜치 `merge`, 정렬 성능 비교는 사용자 요청에 따라 제외했습니다.

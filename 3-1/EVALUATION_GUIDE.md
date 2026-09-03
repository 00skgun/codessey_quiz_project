# Mini Redis 평가 요소 설명서

이 문서는 평가표 순서대로 프로그램의 동작 원리와 답변할 내용을 정리한 발표·구두평가용 자료입니다.

## 1. 필수 기능 평가

### String 명령어

| 명령 | 동작 | 출력 |
|---|---|---|
| `SET key value` | 값을 저장하고 해당 키를 LRU의 최신 위치로 이동합니다. 기존 키를 덮어쓰면 TTL을 제거합니다. | `OK` |
| `GET key` | 만료 여부를 먼저 검사한 뒤 값을 조회합니다. 성공한 경우에만 LRU를 갱신합니다. | `"value"` 또는 `(nil)` |
| `DEL key` | 해시맵, LRU 리스트, TTL 정보에서 키를 함께 제거합니다. | `(integer) 0/1` |
| `EXISTS key` | 만료 정리 후 키가 존재하는지 확인합니다. | `(integer) 0/1` |
| `DBSIZE` | 만료 정리 후 저장된 키 개수를 반환합니다. | `(integer) N` |
| `KEYS` | 해시맵의 모든 버킷을 순회해 키를 출력합니다. 순서는 보장하지 않습니다. | 번호 목록 또는 `(empty array)` |

구현 위치: `mini_redis.py`의 `MiniRedis.set`, `get`, `delete`, `exists`, `dbsize`, `keys`, `execute`

### LRU 자동 제거

LRU는 Least Recently Used의 약자로, 가장 오랫동안 사용하지 않은 데이터를 먼저 제거하는 정책입니다.

- 이중 연결 리스트의 앞(`head`)에는 가장 최근 사용한 키를 둡니다.
- 뒤(`tail`)에는 가장 오래 사용하지 않은 키를 둡니다.
- 성공한 `SET`과 `GET`은 노드를 앞으로 이동시킵니다.
- `SET` 후 `used_memory > maxmemory`이면 뒤의 노드를 하나씩 제거합니다.
- LRU로 제거한 키마다 `evicted_keys`가 증가합니다.
- 만료나 `DEL`로 삭제한 키는 LRU 제거가 아니므로 `evicted_keys`에 포함하지 않습니다.

구현 위치: `mini_redis.py`의 `_evict_if_needed`, `structures/doubly_linked_list.py`

### 메모리 정보

과제 명세에 따라 자료구조 오버헤드는 제외하고 UTF-8 키와 값의 크기만 계산합니다.

```text
used_memory = 합계(UTF-8 key 바이트 수 + UTF-8 value 바이트 수)
```

한글 한 글자는 일반적으로 UTF-8에서 3바이트이므로 `SET 한 글`은 6바이트입니다. 덮어쓰기할 때는 기존 엔트리 크기를 먼저 빼고 새 엔트리 크기를 더합니다.

`INFO memory` 출력:

```text
used_memory:<number>
maxmemory:<number>
evicted_keys:<number>
```

### TTL 관리

TTL은 Time To Live의 약자로, 데이터가 살아 있을 시간을 의미합니다.

- `EXPIRE key seconds`는 `현재 시각 + seconds`를 만료 시각으로 저장합니다.
- `(expire_at, key)` 항목을 최소 힙에 추가합니다.
- `TTL key`는 키 없음 -2, 만료 설정 없음 -1, 설정 있음은 남은 초를 반환합니다.
- `seconds <= 0`이면 즉시 만료시켜 키를 삭제합니다.
- 만료된 키는 데이터와 LRU에서 함께 제거됩니다.
- 같은 키의 TTL을 다시 설정한 경우 예전 힙 항목은 나중에 루트에 도달했을 때 무시합니다. 이를 lazy deletion이라고 합니다.

구현 위치: `mini_redis.py`의 `_purge_expired`, `expire`, `ttl`, `structures/min_heap.py`

### 오류 처리

프로그램은 다음 Redis 스타일 오류를 반환합니다.

```text
(error) ERR unknown command '<CMD>'
(error) ERR wrong number of arguments for '<CMD>' command
(error) ERR value is not an integer or out of range
(error) OOM command not allowed when used_memory > 'maxmemory'
```

단일 키와 값의 크기가 `maxmemory`보다 크면 저장 상태를 변경하지 않고 OOM을 반환합니다. 따라서 기존 키 덮어쓰기가 실패해도 원래 값이 보존됩니다.

## 2. 직접 구현 자료구조 설명

### 이중 연결 리스트

각 `DoublyLinkedNode`는 다음 필드를 가집니다.

- `prev`: 이전 노드
- `next`: 다음 노드
- `data`: 실제 저장 데이터

리스트가 `head`와 `tail`을 보관하고 노드를 직접 전달받기 때문에 아래 연산은 모두 O(1)입니다.

- `insert_front`, `insert_back`
- `remove_front`, `remove_back`
- `remove_node`
- `move_to_front`

LRU에서는 해시맵의 `Entry`가 자신의 리스트 노드를 참조하므로, 리스트에서 키를 다시 찾지 않고 바로 이동할 수 있습니다.

### 직접 설계한 해시 함수

`HashMap`은 64비트 FNV-1a 해시를 사용합니다.

1. 해시를 FNV 초기값 `14695981039346656037`로 시작합니다.
2. 키를 UTF-8 바이트로 변환합니다.
3. 각 바이트에 대해 기존 해시와 XOR 연산을 합니다.
4. FNV 소수 `1099511628211`을 곱하고 64비트로 제한합니다.
5. `hash % bucket_capacity`로 버킷 인덱스를 계산합니다.

내장 문자열 해시에 의존하지 않으며, 영문과 한글 키를 같은 절차로 처리합니다.

### 체이닝 충돌 해결

서로 다른 키가 같은 버킷 인덱스를 얻는 것을 해시 충돌이라고 합니다. 각 버킷에는 `BucketNode(key, value, next)` 단일 연결 리스트를 두었습니다.

- 새 키는 해당 버킷 체인의 앞에 연결합니다.
- 조회는 같은 버킷의 체인만 순회하며 키를 비교합니다.
- 삭제는 이전 노드의 `next`를 삭제 대상의 다음 노드에 연결합니다.

충돌한 키도 별도 노드에 보존되므로 값을 잃지 않습니다.

### 로드 팩터 0.75와 버킷 확장

로드 팩터는 `저장 항목 수 / 버킷 수`입니다. 새 키 삽입으로 0.75를 초과할 예정이면 다음 순서로 확장합니다.

1. 기존의 두 배 크기로 새 버킷 배열을 만듭니다.
2. 기존의 모든 버킷과 체인 노드를 순회합니다.
3. 새 버킷 수를 기준으로 각 키의 인덱스를 다시 계산합니다.
4. 노드를 새 버킷 체인에 재연결합니다.
5. 새 키를 삽입합니다.

버킷 수가 달라지면 나머지 연산의 결과도 달라지므로 모든 키를 재배치해야 합니다. 한 번의 확장은 O(n)이지만 자주 발생하지 않으므로 삽입의 평균 분할 상환 시간은 O(1)입니다.

## 3. LRU와 TTL 동작 원리

### 해시맵과 이중 연결 리스트가 모두 필요한 이유

- 해시맵만 사용하면 키 조회는 평균 O(1)이지만 가장 오래된 키를 바로 알 수 없습니다.
- 리스트만 사용하면 오래된 키는 바로 알 수 있지만 특정 키를 찾는 데 O(n)이 필요합니다.
- 해시맵으로 `Entry`를 평균 O(1)에 찾고, `Entry.lru_node`로 리스트 노드를 O(1)에 이동합니다.

따라서 `조회(해시맵) + 최근 사용 갱신(리스트 이동)`을 평균 O(1)에 수행할 수 있습니다.

### TTL에 힙을 사용하는 이유

최소 힙의 루트에는 가장 작은 값이 위치합니다. 만료 시각을 기준으로 최소 힙을 만들면 다음에 만료될 키가 항상 루트에 있습니다.

- 다음 만료 확인: O(1)
- TTL 추가: O(log n)
- 만료 항목 제거: O(log n)

모든 키를 매번 순회하는 O(n) 방식보다 만료 키를 빠르게 찾을 수 있습니다.

### 메모리 초과 시 eviction 순서

1. 먼저 현재 시각까지 만료된 키를 정리합니다.
2. 새 키와 값의 UTF-8 바이트 크기를 계산합니다.
3. 단일 엔트리 자체가 제한보다 크면 OOM을 반환합니다.
4. 신규 저장 또는 덮어쓰기에 맞게 `used_memory`를 갱신합니다.
5. 성공한 SET 항목을 LRU 리스트 앞으로 옮깁니다.
6. 사용량이 제한 이하가 될 때까지 리스트 뒤의 LRU 키를 삭제합니다.
7. 삭제한 크기를 `used_memory`에서 빼고 `evicted_keys`를 증가시킵니다.

### GET 명령의 전체 흐름

1. TTL 최소 힙을 확인해 현재 시각까지 만료된 키를 삭제합니다.
2. 해시맵에서 대상 키를 찾습니다.
3. 키가 없으면 `(nil)`을 반환하고 LRU는 변경하지 않습니다.
4. 키가 있으면 값을 읽습니다.
5. 해당 LRU 노드를 리스트 앞으로 이동합니다.
6. 값을 큰따옴표로 감싸 반환합니다.

만료된 키는 1단계에서 삭제되므로 성공한 조회로 처리되지 않고 LRU도 갱신되지 않습니다.

## 4. 확장 질문 답변

### LRU 대신 LFU를 구현한다면

LFU는 Least Frequently Used, 즉 사용 빈도가 가장 낮은 키를 제거합니다.

- `Entry`에 `frequency`와 빈도 리스트 노드 참조를 추가합니다.
- `frequency -> 이중 연결 리스트`를 저장하는 별도 해시맵을 둡니다.
- 현재 가장 작은 빈도를 나타내는 `min_frequency`를 관리합니다.
- GET/SET 성공 시 기존 빈도 리스트에서 노드를 빼고 다음 빈도 리스트로 옮깁니다.
- 제거할 때 `min_frequency` 리스트의 꼬리를 선택합니다.
- 사용 빈도가 같으면 리스트 안의 LRU 순서로 동률을 해결합니다.

평균 O(1) LFU가 가능하지만 빈도별 리스트와 메타데이터가 추가되어 LRU보다 메모리와 구현 복잡도가 증가합니다. 오래전에 많이 사용된 키가 계속 남는 문제를 줄이려면 빈도를 주기적으로 감소시키는 aging도 필요합니다.

### 데이터가 10만 건이면 예상되는 병목

- 해시맵 확장 시 모든 노드를 한 번에 옮겨 특정 SET이 오래 걸릴 수 있습니다. 명령마다 일부 버킷만 옮기는 incremental rehash로 개선할 수 있습니다.
- 충돌 체인이 길어지면 조회가 최악 O(n)이 됩니다. 더 강한 시드 기반 해시와 충돌 길이 모니터링을 적용할 수 있습니다.
- TTL을 반복 변경하면 lazy heap 레코드가 쌓입니다. 힙 크기가 실제 TTL 키 수의 일정 배수를 넘으면 활성 TTL로 힙을 재구축할 수 있습니다.
- `KEYS`는 모든 키를 한 번에 순회하고 출력해 O(n) 시간과 큰 결과 버퍼가 필요합니다. 커서 기반 `SCAN`으로 나누어 반환할 수 있습니다.
- 키마다 Entry, 버킷 노드, LRU 노드 객체가 존재합니다. 슬롯, 인덱스 기반 배열, 객체 풀로 메모리 사용과 캐시 지역성을 개선할 수 있습니다.
- 하나의 큰 SET이 많은 LRU 키를 연속 제거할 수 있습니다. 실제 서비스에서는 근사 LRU 샘플링이나 백그라운드 제거를 고려할 수 있습니다.

### 자료구조 오버헤드를 used_memory에 포함한다면

현재는 평가 명세에 따라 키와 값의 UTF-8 payload만 계산합니다. 실제 메모리를 계산하려면 다음 항목도 포함해야 합니다.

- Entry, 버킷 노드, LRU 노드, 힙 항목의 객체 헤더와 필드
- 버킷 배열과 동적 배열의 비어 있는 예약 슬롯
- 문자열 객체와 포인터 정렬 비용
- TTL 갱신으로 남은 lazy heap 레코드

이 비용을 포함하면 같은 `maxmemory`에서 저장 가능한 키 수가 줄어들고 eviction과 OOM이 더 빨리 발생합니다. 공정한 비교를 위해 Python 버전, 32/64비트 환경, 메모리 할당자, 데이터와 명령 순서를 동일하게 고정해야 합니다. `sys.getsizeof`를 중복 참조 없이 재귀 합산하거나 동일 워크로드 전후의 프로세스 RSS 차이를 측정할 수 있습니다. payload와 실제 프로세스 메모리는 의미가 다르므로 두 수치를 별도 지표로 표시해야 합니다.

## 5. 보너스 구현

| 보너스 | 구현 파일 | 내용 |
|---|---|---|
| 동적 배열 | `structures/dynamic_array.py` | `append/get/set/remove`, capacity 2배 확장 |
| 스택/큐/덱 | `structures/linear_collections.py` | 직접 구현 배열과 리스트 재사용 |
| 이진 트리 | `structures/binary_tree.py` | 배열 표현, 전위/중위/후위/레벨 순회 |
| BST | `structures/binary_search_tree.py` | 삽입, 탐색, 삭제, 중위 정렬 |
| Pub/Sub | `pubsub.py` | 채널 연결 리스트와 구독자별 메시지 큐 |

스택, 큐, 덱에 대한 별도 설명은 `STACK_QUEUE_DEQUE.md`에 있습니다.

## 평가 시연 순서

아래 명령을 순서대로 실행하면 주요 기능을 짧게 보여줄 수 있습니다.

```text
CONFIG SET maxmemory 30
SET user:1 "Alice"
SET user:2 "Bob"
GET user:1
SET user:3 "Charlie"
INFO memory
KEYS
EXPIRE user:1 3
TTL user:1
GET user:1
DEL user:2
EXISTS user:2
DBSIZE
CONFIG SET maxmemory abc
GET
HELLO
```

LRU 갱신을 보여주기 위해 `user:3`을 저장하기 전에 `GET user:1`을 실행합니다. 그러면 `user:1`이 최신 키가 되고, 메모리 초과 시 더 오래 사용하지 않은 `user:2`가 먼저 제거됩니다. TTL은 `EXPIRE` 후 3초 이상 기다린 다음 `GET`하면 `(nil)`을 확인할 수 있습니다.

## 자동 검증

```bash
python -m unittest discover -v
```

테스트는 필수 명령, LRU, OOM, UTF-8 메모리, TTL 재설정, 오류 형식, 해시 충돌·확장, 힙, 이중 연결 리스트와 모든 보너스 기능을 검증합니다.

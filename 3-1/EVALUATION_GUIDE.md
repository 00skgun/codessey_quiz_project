# Mini Redis 평가 요소 설명서

이 문서는 평가표 순서대로 프로그램의 동작 원리와 답변할 내용을 정리한 발표·구두평가용 자료입니다.

## 0. 전체 구조 먼저 이해하기

Mini Redis는 하나의 데이터를 세 자료구조가 서로 다른 목적으로 관리합니다.

```text
사용자 명령
    ↓
MiniRedis.execute() - 명령어와 인자 검사
    ↓
MiniRedis 핵심 로직
    ├─ HashMap: key로 Entry를 빠르게 찾음
    ├─ DoublyLinkedList: 최근 사용 순서를 관리함
    └─ MinHeap: 가장 빠른 TTL 만료를 관리함
```

해시맵에 저장되는 실제 값은 단순 문자열이 아니라 `Entry` 객체입니다.

```text
Entry
├─ key: "user:1"
├─ value: "Alice"
├─ lru_node: LRU 리스트의 user:1 노드를 가리키는 참조
└─ expire_at: 만료 시각, TTL이 없으면 None
```

예를 들어 `GET user:1`이 실행되면 해시맵에서 `Entry`를 찾고, `Entry.lru_node`를 이용해 LRU 노드를 바로 앞으로 옮깁니다. `lru_node`가 없다면 LRU 리스트를 처음부터 검색해야 하므로 O(n)이 됩니다.

> **평가 때 한 문장으로:** 해시맵은 키 조회, 이중 연결 리스트는 LRU 순서, 최소 힙은 TTL 만료 순서를 담당하며, Entry가 이 자료구조들을 연결합니다.

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

#### 기본 명령 실행 예시

```text
mini-redis> SET name "Alice Kim"
OK

mini-redis> GET name
"Alice Kim"

mini-redis> EXISTS name
(integer) 1

mini-redis> DBSIZE
(integer) 1

mini-redis> KEYS
1. "name"

mini-redis> DEL name
(integer) 1

mini-redis> GET name
(nil)

mini-redis> EXISTS name
(integer) 0
```

`DEL`은 해시맵에서만 키를 지우는 것이 아닙니다. 해당 `Entry.lru_node`도 LRU 리스트에서 제거하고 `expire_at`도 무효화하며, 키와 값의 크기를 `used_memory`에서 뺍니다.

#### SET으로 기존 키를 덮어쓰는 예시

```text
mini-redis> SET user "old"
OK
mini-redis> EXPIRE user 100
(integer) 1
mini-redis> SET user "new"
OK
mini-redis> TTL user
(integer) -1
mini-redis> GET user
"new"
```

기존 키를 `SET`으로 덮어쓰면 값과 메모리 사용량을 갱신하고, 과제 규칙에 따라 기존 TTL을 삭제합니다.

> **평가 때 답변:** 키 기반 명령은 먼저 만료를 확인합니다. SET과 성공한 GET만 LRU를 갱신하고, DEL은 해시맵·LRU·TTL·메모리 정보를 함께 정리합니다.

### LRU 자동 제거

LRU는 Least Recently Used의 약자로, 가장 오랫동안 사용하지 않은 데이터를 먼저 제거하는 정책입니다.

- 이중 연결 리스트의 앞(`head`)에는 가장 최근 사용한 키를 둡니다.
- 뒤(`tail`)에는 가장 오래 사용하지 않은 키를 둡니다.
- 성공한 `SET`과 `GET`은 노드를 앞으로 이동시킵니다.
- `SET` 후 `used_memory > maxmemory`이면 뒤의 노드를 하나씩 제거합니다.
- LRU로 제거한 키마다 `evicted_keys`가 증가합니다.
- 만료나 `DEL`로 삭제한 키는 LRU 제거가 아니므로 `evicted_keys`에 포함하지 않습니다.

구현 위치: `mini_redis.py`의 `_evict_if_needed`, `structures/doubly_linked_list.py`

#### GET이 LRU 순서를 바꾸는 예시

초기 메모리 제한을 30바이트로 설정합니다.

```text
mini-redis> CONFIG SET maxmemory 30
OK
mini-redis> SET user:1 "Alice"
OK
mini-redis> SET user:2 "Bob"
OK
```

이때 LRU 순서는 다음과 같습니다.

```text
head                                      tail
[user:2, 최근] ⇄ [user:1, 오래됨]
```

`GET user:1`을 실행하면 `user:1`을 사용했으므로 앞으로 이동합니다.

```text
mini-redis> GET user:1
"Alice"

head                                      tail
[user:1, 최근] ⇄ [user:2, 오래됨]
```

이제 `user:3`을 저장합니다.

```text
mini-redis> SET user:3 "Charlie"
OK
```

세 엔트리의 총크기는 33바이트이므로 제한 30바이트를 초과합니다. 새 키 `user:3`은 가장 최근 위치에 추가되고, tail의 `user:2`가 제거됩니다.

```text
제거 전: head [user:3] ⇄ [user:1] ⇄ [user:2] tail
제거 후: head [user:3] ⇄ [user:1] tail
```

```text
mini-redis> GET user:2
(nil)
mini-redis> GET user:1
"Alice"
```

> **평가 때 답변:** 해시맵에서 찾은 Entry의 `lru_node`를 이용해 성공한 GET 항목을 head로 옮깁니다. 메모리 초과 시 tail에 있는 가장 오래 사용하지 않은 키부터 삭제합니다.

### 메모리 정보

과제 명세에 따라 자료구조 오버헤드는 제외하고 UTF-8 키와 값의 크기만 계산합니다.

```text
used_memory = 합계(UTF-8 key 바이트 수 + UTF-8 value 바이트 수)
```

한글 한 글자는 일반적으로 UTF-8에서 3바이트이므로 `SET 한 글`은 6바이트입니다. 덮어쓰기할 때는 기존 엔트리 크기를 먼저 빼고 새 엔트리 크기를 더합니다.

#### 메모리 계산 예시

```text
SET user:1 "Alice"
```

- `user:1`: 영문 6바이트
- `Alice`: 영문 5바이트
- 엔트리 크기: `6 + 5 = 11바이트`

```text
SET user:2 "Bob"       → 6 + 3 = 9바이트
SET user:3 "Charlie"   → 6 + 7 = 13바이트
```

세 엔트리가 모두 있으면 다음과 같습니다.

```text
used_memory = 11 + 9 + 13 = 33바이트
```

`maxmemory`가 30이고 `user:2`가 LRU로 제거되면 9바이트가 빠집니다.

```text
used_memory = 33 - 9 = 24바이트
evicted_keys = 1
```

한글도 글자 수가 아니라 UTF-8 바이트로 계산합니다.

```text
SET 한 글
key "한" = 3바이트
value "글" = 3바이트
used_memory = 6바이트
```

`INFO memory` 출력:

```text
used_memory:<number>
maxmemory:<number>
evicted_keys:<number>
```

> **평가 때 답변:** used_memory는 과제 공식에 따라 UTF-8 key와 value의 바이트만 더합니다. SET 덮어쓰기는 기존 크기를 빼고 새 크기를 더하며, LRU 삭제 시 삭제한 크기를 다시 뺍니다.

### TTL 관리

TTL은 Time To Live의 약자로, 데이터가 살아 있을 시간을 의미합니다.

- `EXPIRE key seconds`는 `현재 시각 + seconds`를 만료 시각으로 저장합니다.
- `(expire_at, key)` 항목을 최소 힙에 추가합니다.
- `TTL key`는 키 없음 -2, 만료 설정 없음 -1, 설정 있음은 남은 초를 반환합니다.
- `seconds <= 0`이면 즉시 만료시켜 키를 삭제합니다.
- 만료된 키는 데이터와 LRU에서 함께 제거됩니다.
- 같은 키의 TTL을 다시 설정한 경우 예전 힙 항목은 나중에 루트에 도달했을 때 무시합니다. 이를 lazy deletion이라고 합니다.

구현 위치: `mini_redis.py`의 `_purge_expired`, `expire`, `ttl`, `structures/min_heap.py`

#### TTL 시간 흐름 예시

현재 시각을 이해하기 쉽게 100초라고 가정합니다.

```text
mini-redis> SET code "1234"
OK
mini-redis> EXPIRE code 5
(integer) 1
```

내부에서는 다음 정보가 저장됩니다.

```text
Entry.expire_at = 100 + 5 = 105
MinHeap에 (105, "code") 추가
```

102초 시점에는 아직 살아 있습니다.

```text
mini-redis> TTL code
(integer) 3
mini-redis> GET code
"1234"
```

106초 시점에 다음 명령이 들어오면 최소 힙의 루트가 현재 시각보다 작으므로 삭제합니다.

```text
HashMap에서 code 삭제
LRU 리스트에서 code 노드 삭제
used_memory에서 code 크기 차감
```

```text
mini-redis> GET code
(nil)
mini-redis> TTL code
(integer) -2
```

TTL이 없는 키와 없는 키는 구분됩니다.

```text
mini-redis> SET permanent "data"
OK
mini-redis> TTL permanent
(integer) -1
mini-redis> TTL missing
(integer) -2
```

#### TTL을 다시 설정하는 lazy deletion 예시

```text
EXPIRE session 10   → 힙에 (110, session)
EXPIRE session 30   → 힙에 (130, session), Entry.expire_at은 130
```

110초가 되어 예전 `(110, session)`이 힙 루트에 올라와도 `Entry.expire_at`은 130이므로 삭제하지 않습니다. 130초가 되었을 때 현재 Entry와 만료 시각이 일치하므로 실제로 삭제합니다.

> **평가 때 답변:** 최소 힙의 루트에 가장 빠른 만료가 있으므로 다음 만료 확인은 O(1)입니다. TTL을 재설정해서 남은 옛 레코드는 현재 Entry의 expire_at과 비교해 무시하는 lazy deletion을 사용했습니다.

### 오류 처리

프로그램은 다음 Redis 스타일 오류를 반환합니다.

```text
(error) ERR unknown command '<CMD>'
(error) ERR wrong number of arguments for '<CMD>' command
(error) ERR value is not an integer or out of range
(error) OOM command not allowed when used_memory > 'maxmemory'
```

단일 키와 값의 크기가 `maxmemory`보다 크면 저장 상태를 변경하지 않고 OOM을 반환합니다. 따라서 기존 키 덮어쓰기가 실패해도 원래 값이 보존됩니다.

#### 오류 실행 예시

```text
mini-redis> HELLO
(error) ERR unknown command 'HELLO'

mini-redis> GET
(error) ERR wrong number of arguments for 'GET' command

mini-redis> CONFIG SET maxmemory abc
(error) ERR value is not an integer or out of range

mini-redis> EXPIRE key 1.5
(error) ERR value is not an integer or out of range
```

OOM은 단일 엔트리만으로 제한을 초과하는 상황을 보여주면 명확합니다.

```text
mini-redis> CONFIG SET maxmemory 5
OK
mini-redis> SET big "123456"
(error) OOM command not allowed when used_memory > 'maxmemory'
mini-redis> GET big
(nil)
```

> **평가 때 답변:** execute에서 명령별 인자 수를 먼저 확인하고, 64비트 십진 정수 전용 파서로 잘못된 정수를 거릅니다. 단일 엔트리가 maxmemory보다 크면 저장 전 OOM을 반환하므로 기존 상태가 손상되지 않습니다.

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

#### `move_to_front` 예시

```text
이동 전
head [A] ⇄ [B] ⇄ [C] tail

GET B 실행
```

`B.prev`인 A와 `B.next`인 C를 연결하고, B를 기존 head 앞에 연결합니다.

```text
이동 후
head [B] ⇄ [A] ⇄ [C] tail
```

전체 리스트를 복사하거나 다시 만들지 않고 B 주변의 포인터와 head만 변경합니다. 따라서 리스트 길이와 관계없이 O(1)입니다.

#### 체이닝 리스트와 LRU 리스트의 차이

두 리스트는 목적이 다르므로 혼동하면 안 됩니다.

| 구조 | 목적 | 형태 |
|---|---|---|
| 해시맵 버킷의 체이닝 | 같은 해시 인덱스의 충돌 해결 | `BucketNode` 단일 연결 리스트 |
| LRU 리스트 | 전체 키의 최근 사용 순서 관리 | `DoublyLinkedNode` 이중 연결 리스트 |

즉, 해시맵과 LRU 이중 연결 리스트를 함께 쓰는 이유는 체이닝 때문이 아니라 **키 조회와 LRU 갱신을 모두 평균 O(1)에 만들기 위해서**입니다.

> **평가 때 답변:** 노드는 prev, next, data를 가지고 있습니다. Entry가 리스트 노드를 직접 참조하므로 remove_node와 move_to_front는 탐색 없이 주변 포인터만 변경해 O(1)입니다.

### 직접 설계한 해시 함수

`HashMap`은 64비트 FNV-1a 해시를 사용합니다.

1. 해시를 FNV 초기값 `14695981039346656037`로 시작합니다.
2. 키를 UTF-8 바이트로 변환합니다.
3. 각 바이트에 대해 기존 해시와 XOR 연산을 합니다.
4. FNV 소수 `1099511628211`을 곱하고 64비트로 제한합니다.
5. `hash % bucket_capacity`로 버킷 인덱스를 계산합니다.

내장 문자열 해시에 의존하지 않으며, 영문과 한글 키를 같은 절차로 처리합니다.

#### 해시 인덱스 계산 예시

버킷이 8개라고 가정하면 인덱스는 항상 0부터 7 사이입니다.

```text
key = "name"
UTF-8 bytes = [110, 97, 109, 101]
FNV-1a로 각 바이트를 XOR하고 곱셈
최종 index = hash("name") % 8
```

버킷 배열 전체를 검색하지 않고 계산된 한 버킷으로 바로 이동합니다. 평균적으로 버킷의 체인이 짧게 유지되면 조회가 O(1)입니다.

> **평가 때 답변:** 문자열 키를 UTF-8 바이트로 만들고 FNV-1a의 XOR과 곱셈을 반복한 뒤 버킷 개수로 나눈 나머지를 인덱스로 사용합니다.

### 체이닝 충돌 해결

서로 다른 키가 같은 버킷 인덱스를 얻는 것을 해시 충돌이라고 합니다. 각 버킷에는 `BucketNode(key, value, next)` 단일 연결 리스트를 두었습니다.

- 새 키는 해당 버킷 체인의 앞에 연결합니다.
- 조회는 같은 버킷의 체인만 순회하며 키를 비교합니다.
- 삭제는 이전 노드의 `next`를 삭제 대상의 다음 노드에 연결합니다.

충돌한 키도 별도 노드에 보존되므로 값을 잃지 않습니다.

#### 실제 충돌 예시

현재 구현에서 버킷 수가 8일 때 `"a"`와 `"i"`는 같은 인덱스 4가 됩니다.

```text
hash_index("a") = 4
hash_index("i") = 4
```

먼저 `a`를 넣고 `i`를 넣으면 다음과 같은 체인이 만들어집니다.

```text
buckets[4]
    ↓
[key="i", value=2] → [key="a", value=1] → None
```

`get("a")`는 4번 버킷으로 이동한 뒤 `i`와 `a`를 실제 문자열로 비교해 올바른 값을 찾습니다. 해시값이나 인덱스가 같아도 키 문자열까지 비교하므로 잘못된 값을 반환하지 않습니다.

> **평가 때 답변:** 충돌한 데이터를 버리지 않고 BucketNode의 next로 연결합니다. 조회 시 같은 버킷 체인을 순회하면서 실제 key가 일치하는 노드를 선택합니다.

### 로드 팩터 0.75와 버킷 확장

로드 팩터는 `저장 항목 수 / 버킷 수`입니다. 새 키 삽입으로 0.75를 초과할 예정이면 다음 순서로 확장합니다.

1. 기존의 두 배 크기로 새 버킷 배열을 만듭니다.
2. 기존의 모든 버킷과 체인 노드를 순회합니다.
3. 새 버킷 수를 기준으로 각 키의 인덱스를 다시 계산합니다.
4. 노드를 새 버킷 체인에 재연결합니다.
5. 새 키를 삽입합니다.

버킷 수가 달라지면 나머지 연산의 결과도 달라지므로 모든 키를 재배치해야 합니다. 한 번의 확장은 O(n)이지만 자주 발생하지 않으므로 삽입의 평균 분할 상환 시간은 O(1)입니다.

#### 숫자로 보는 확장 예시

초기 버킷이 8개일 때 6개 엔트리가 들어 있으면 로드 팩터는 정확히 0.75입니다.

```text
현재: 6 / 8 = 0.75
7번째 삽입 예정: (6 + 1) / 8 = 0.875
```

0.875는 0.75보다 크므로 7번째 키를 넣기 전에 버킷을 16개로 확장합니다.

```text
확장 후: 6 / 16 = 0.375
7번째 삽입 후: 7 / 16 = 0.4375
```

예를 들어 기존에 `hash(key) % 8 = 3`이었던 키도 `hash(key) % 16`에서는 3 또는 11이 될 수 있습니다. 그래서 기존 버킷 위치를 그대로 복사하지 않고 모든 노드를 새 인덱스로 다시 배치합니다.

> **평가 때 답변:** 새 키 삽입 예정 로드 팩터가 0.75를 넘으면 버킷을 두 배로 만들고, 새 capacity로 모든 기존 키의 인덱스를 다시 계산해 재배치한 후 새 키를 넣습니다.

## 3. LRU와 TTL 동작 원리

### 해시맵과 이중 연결 리스트가 모두 필요한 이유

- 해시맵만 사용하면 키 조회는 평균 O(1)이지만 가장 오래된 키를 바로 알 수 없습니다.
- 리스트만 사용하면 오래된 키는 바로 알 수 있지만 특정 키를 찾는 데 O(n)이 필요합니다.
- 해시맵으로 `Entry`를 평균 O(1)에 찾고, `Entry.lru_node`로 리스트 노드를 O(1)에 이동합니다.

따라서 `조회(해시맵) + 최근 사용 갱신(리스트 이동)`을 평균 O(1)에 수행할 수 있습니다.

#### 하나만 사용했을 때의 문제 예시

키가 10만 개 있다고 가정합니다.

- 리스트만 있으면 `GET user:99999`를 찾기 위해 최악의 경우 노드 10만 개를 확인해야 합니다.
- 해시맵만 있으면 키는 빨리 찾지만 10만 개 중 무엇이 가장 오래 사용되지 않았는지 바로 알 수 없습니다.
- 해시맵과 이중 연결 리스트를 결합하면 해시맵으로 Entry를 찾고 `Entry.lru_node`를 바로 이동합니다.

```text
HashMap
"B" → Entry(value, lru_node) ──────────┐
                                       ↓
LRU: head [A] ⇄ [B] ⇄ [C] tail

GET B 후: head [B] ⇄ [A] ⇄ [C] tail
```

> **평가 때 답변:** 해시맵은 키 조회를 평균 O(1)로 만들고, 이중 연결 리스트는 임의 노드의 이동과 tail 삭제를 O(1)로 만듭니다. 둘을 Entry.lru_node로 연결해야 O(1) LRU가 가능합니다.

### TTL에 힙을 사용하는 이유

최소 힙의 루트에는 가장 작은 값이 위치합니다. 만료 시각을 기준으로 최소 힙을 만들면 다음에 만료될 키가 항상 루트에 있습니다.

- 다음 만료 확인: O(1)
- TTL 추가: O(log n)
- 만료 항목 제거: O(log n)

모든 키를 매번 순회하는 O(n) 방식보다 만료 키를 빠르게 찾을 수 있습니다.

#### 최소 힙 예시

다음 TTL 세 개를 설정했다고 가정합니다.

```text
A는 130초에 만료
B는 110초에 만료
C는 120초에 만료
```

최소 힙은 다음처럼 가장 빠른 110초를 루트에 둡니다.

```text
          (110, B)
          /      \
    (130, A)   (120, C)
```

현재 시각이 115초라면 루트 B를 제거합니다. 다음 루트는 C가 되어 아직 만료되지 않았음을 확인하고 정리를 멈춥니다. A까지 전부 검사할 필요가 없습니다.

> **평가 때 답변:** expire_at을 우선순위로 하는 최소 힙을 사용해 가장 빠른 만료가 항상 루트에 오게 했습니다. 루트 확인은 O(1), 추가와 삭제는 O(log n)입니다.

### 메모리 초과 시 eviction 순서

1. 먼저 현재 시각까지 만료된 키를 정리합니다.
2. 새 키와 값의 UTF-8 바이트 크기를 계산합니다.
3. 단일 엔트리 자체가 제한보다 크면 OOM을 반환합니다.
4. 신규 저장 또는 덮어쓰기에 맞게 `used_memory`를 갱신합니다.
5. 성공한 SET 항목을 LRU 리스트 앞으로 옮깁니다.
6. 사용량이 제한 이하가 될 때까지 리스트 뒤의 LRU 키를 삭제합니다.
7. 삭제한 크기를 `used_memory`에서 빼고 `evicted_keys`를 증가시킵니다.

#### eviction 수치 예시

```text
maxmemory = 30

user:1 + Alice   = 11바이트
user:2 + Bob     =  9바이트
user:3 + Charlie = 13바이트
합계              = 33바이트
```

LRU 순서가 다음과 같다고 가정합니다.

```text
head [user:3] ⇄ [user:1] ⇄ [user:2] tail
```

33바이트는 제한보다 3바이트 많지만 정확히 3바이트만 잘라낼 수는 없습니다. 하나의 완전한 엔트리를 제거해야 하므로 tail의 `user:2` 9바이트를 삭제합니다.

```text
used_memory = 33 - 9 = 24
evicted_keys = 0 + 1 = 1
```

24는 30 이하이므로 제거를 멈춥니다. 만약 여전히 제한을 초과했다면 다음 tail도 계속 제거합니다.

> **평가 때 답변:** SET 후 사용량이 제한보다 큰 동안 LRU tail을 반복 삭제합니다. 삭제한 key와 value 크기를 used_memory에서 빼고 evicted_keys를 1 증가시킵니다.

### GET 명령의 전체 흐름

1. TTL 최소 힙을 확인해 현재 시각까지 만료된 키를 삭제합니다.
2. 해시맵에서 대상 키를 찾습니다.
3. 키가 없으면 `(nil)`을 반환하고 LRU는 변경하지 않습니다.
4. 키가 있으면 값을 읽습니다.
5. 해당 LRU 노드를 리스트 앞으로 이동합니다.
6. 값을 큰따옴표로 감싸 반환합니다.

만료된 키는 1단계에서 삭제되므로 성공한 조회로 처리되지 않고 LRU도 갱신되지 않습니다.

#### 성공한 GET과 만료된 GET 비교

성공한 경우:

```text
GET user:1
→ TTL 만료 아님
→ HashMap에서 Entry 발견
→ value "Alice" 확보
→ Entry.lru_node를 head로 이동
→ "Alice" 반환
```

만료된 경우:

```text
GET session
→ TTL 힙에서 session 만료 확인
→ HashMap과 LRU에서 session 삭제
→ HashMap 조회 결과 없음
→ (nil) 반환
→ LRU 갱신하지 않음
```

> **평가 때 답변:** GET은 TTL 확인, 삭제 여부 판단, 해시 조회, 값 확보, LRU 갱신 순서로 동작합니다. 값 반환에 성공한 경우에만 LRU를 갱신합니다.

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

#### LFU 제거 예시

```text
A: 5회 사용
B: 1회 사용
C: 1회 사용
```

LFU에서는 사용 횟수가 가장 적은 B 또는 C를 제거해야 합니다. B와 C의 빈도가 같다면 빈도 1의 이중 연결 리스트에서 더 오래 사용되지 않은 키를 제거합니다.

```text
frequency 1: head [C, 최근] ⇄ [B, 오래됨] tail
frequency 5: head [A] tail
min_frequency = 1
```

이 경우 B가 제거됩니다. GET B가 성공하면 B는 frequency 1 리스트에서 빠져 frequency 2 리스트로 이동합니다.

> **평가 때 답변:** Entry에 frequency를 추가하고 빈도별 이중 연결 리스트와 min_frequency를 관리합니다. 최소 빈도의 리스트 tail을 제거하면 빈도 동률도 LRU로 해결할 수 있습니다.

### 데이터가 10만 건이면 예상되는 병목

- 해시맵 확장 시 모든 노드를 한 번에 옮겨 특정 SET이 오래 걸릴 수 있습니다. 명령마다 일부 버킷만 옮기는 incremental rehash로 개선할 수 있습니다.
- 충돌 체인이 길어지면 조회가 최악 O(n)이 됩니다. 더 강한 시드 기반 해시와 충돌 길이 모니터링을 적용할 수 있습니다.
- TTL을 반복 변경하면 lazy heap 레코드가 쌓입니다. 힙 크기가 실제 TTL 키 수의 일정 배수를 넘으면 활성 TTL로 힙을 재구축할 수 있습니다.
- `KEYS`는 모든 키를 한 번에 순회하고 출력해 O(n) 시간과 큰 결과 버퍼가 필요합니다. 커서 기반 `SCAN`으로 나누어 반환할 수 있습니다.
- 키마다 Entry, 버킷 노드, LRU 노드 객체가 존재합니다. 슬롯, 인덱스 기반 배열, 객체 풀로 메모리 사용과 캐시 지역성을 개선할 수 있습니다.
- 하나의 큰 SET이 많은 LRU 키를 연속 제거할 수 있습니다. 실제 서비스에서는 근사 LRU 샘플링이나 백그라운드 제거를 고려할 수 있습니다.

#### 10만 건 상황을 명령에 대입한 예시

```text
SET key:0 value
SET key:1 value
...
SET key:99999 value
```

| 발생 상황 | 문제 | 개선 방법 |
|---|---|---|
| 버킷이 가득 차 확장 | 한 번의 SET에서 10만 노드 재배치 가능 | 명령마다 일부만 옮기는 incremental rehash |
| 모든 키에 TTL을 반복 갱신 | 실제 키보다 lazy 힙 항목이 훨씬 많아짐 | 활성 TTL 수 대비 힙이 너무 크면 재구축 |
| `KEYS` 실행 | 키 10만 개를 한 번에 순회·문자열 생성 | 커서 기반 `SCAN`으로 분할 반환 |
| 큰 값 저장 후 메모리 초과 | 한 명령에서 여러 LRU 키 연속 삭제 | 근사 LRU 또는 백그라운드 제거 |
| 체인 한곳에 충돌 집중 | 평균 O(1)이 최악 O(n)으로 저하 | 시드 기반 해시와 충돌 길이 관측 |

> **평가 때 답변:** 가장 큰 일시 정지는 전체 재해시와 KEYS에서 발생할 수 있고, TTL 재설정은 lazy 항목을 늘릴 수 있습니다. 점진적 재해시, SCAN, 힙 재구축으로 개선할 수 있습니다.

### 자료구조 오버헤드를 used_memory에 포함한다면

현재는 평가 명세에 따라 키와 값의 UTF-8 payload만 계산합니다. 실제 메모리를 계산하려면 다음 항목도 포함해야 합니다.

- Entry, 버킷 노드, LRU 노드, 힙 항목의 객체 헤더와 필드
- 버킷 배열과 동적 배열의 비어 있는 예약 슬롯
- 문자열 객체와 포인터 정렬 비용
- TTL 갱신으로 남은 lazy heap 레코드

이 비용을 포함하면 같은 `maxmemory`에서 저장 가능한 키 수가 줄어들고 eviction과 OOM이 더 빨리 발생합니다. 공정한 비교를 위해 Python 버전, 32/64비트 환경, 메모리 할당자, 데이터와 명령 순서를 동일하게 고정해야 합니다. `sys.getsizeof`를 중복 참조 없이 재귀 합산하거나 동일 워크로드 전후의 프로세스 RSS 차이를 측정할 수 있습니다. payload와 실제 프로세스 메모리는 의미가 다르므로 두 수치를 별도 지표로 표시해야 합니다.

#### payload와 실제 메모리의 차이 예시

과제 공식에서는 다음 엔트리가 2바이트입니다.

```text
key = "a"   → 1바이트
value = "1" → 1바이트
used_memory  → 2바이트
```

하지만 실제 실행 환경에서는 Entry 객체, 버킷 노드, LRU 노드, 문자열 객체, 포인터와 버킷 배열 슬롯까지 필요하므로 실제 RAM 사용량은 2바이트보다 훨씬 큽니다. 정확한 값은 Python 버전과 운영체제에 따라 달라집니다.

예를 들어 두 구현을 비교하면서 한쪽은 payload만 계산하고 다른 쪽은 객체 오버헤드까지 계산하면 같은 `maxmemory`에서도 eviction 시점이 달라져 공정하지 않습니다. 두 구현 모두 동일한 계산 공식, Python 버전, 입력 데이터와 명령 순서를 사용해야 합니다.

> **평가 때 답변:** 오버헤드를 포함하면 Entry, 리스트 노드, 버킷 노드, 힙 항목과 예약 슬롯 비용이 추가되어 eviction이 더 빨리 발생합니다. 공정한 비교를 위해 환경과 워크로드, 측정 도구를 고정하고 payload와 실제 RSS를 구분해서 표시해야 합니다.

## 5. 보너스 구현

| 보너스 | 구현 파일 | 내용 |
|---|---|---|
| 동적 배열 | `structures/dynamic_array.py` | `append/get/set/remove`, capacity 2배 확장 |
| 스택/큐/덱 | `structures/linear_collections.py` | 직접 구현 배열과 리스트 재사용 |
| 이진 트리 | `structures/binary_tree.py` | 배열 표현, 전위/중위/후위/레벨 순회 |
| BST | `structures/binary_search_tree.py` | 삽입, 탐색, 삭제, 중위 정렬 |
| Pub/Sub | `pubsub.py` | 채널 연결 리스트와 구독자별 메시지 큐 |

스택, 큐, 덱에 대한 별도 설명은 `STACK_QUEUE_DEQUE.md`에 있습니다.

### 보너스별 간단한 예시

#### 동적 배열

```text
초기 capacity = 2
append("A") → [A, _]
append("B") → [A, B]
append("C") → 공간 부족
capacity를 4로 확장 → [A, B, C, _]
```

기존 값을 새 배열로 옮기고 capacity를 두 배로 확장합니다. 평상시 append는 O(1), 확장 시에는 O(n)이지만 여러 삽입에 나누어 보면 분할 상환 O(1)입니다.

#### 스택·큐·덱

```text
Stack: push A, push B, pop → B       마지막 입력이 먼저 출력
Queue: enqueue A, enqueue B, dequeue → A   첫 입력이 먼저 출력
Deque: 양쪽에서 삽입과 삭제 가능
```

Queue와 Deque는 직접 구현한 이중 연결 리스트를 사용해 앞과 뒤의 연산을 O(1)로 처리합니다.

#### 이진 트리와 BST

```text
        4
       / \
      2   6
     / \ / \
    1  3 5  7
```

- 중위 순회: `1, 2, 3, 4, 5, 6, 7`
- 전위 순회: `4, 2, 1, 3, 6, 5, 7`
- 후위 순회: `1, 3, 2, 5, 7, 6, 4`
- 레벨 순회: `4, 2, 6, 1, 3, 5, 7`

BST의 중위 순회는 키가 오름차순으로 나옵니다. 삭제는 자식이 없는 경우, 하나인 경우, 둘인 경우를 나누어 처리합니다.

#### Pub/Sub

```text
mini-redis> SUBSCRIBE news alice
(integer) 1
mini-redis> SUBSCRIBE news bob
(integer) 2
mini-redis> PUBLISH news "hello"
(integer) 2
mini-redis> POLL news alice
"hello"
mini-redis> POLL news bob
"hello"
```

채널의 구독자는 연결 리스트로 관리하고 각 구독자에게 독립적인 Queue를 둡니다. 따라서 Alice가 메시지를 꺼내도 Bob의 메시지는 사라지지 않습니다.

## 평가 시연 순서

아래 명령을 순서대로 실행하면 필수 기능을 한 세션에서 보여줄 수 있습니다.

```text
CONFIG SET maxmemory 30
SET user:1 "Alice"
SET user:2 "Bob"
GET user:1
SET user:3 "Charlie"
GET user:2
GET user:1
INFO memory
KEYS
EXPIRE user:1 3
TTL user:1
```

여기에서 3초 이상 기다린 후 이어서 실행합니다.

```text
GET user:1
TTL user:1
DEL user:3
EXISTS user:3
DBSIZE
CONFIG SET maxmemory 5
SET big "123456"
DEL user:2
CONFIG SET maxmemory abc
GET
HELLO
```

이 시연에서 확인할 결과는 다음과 같습니다.

1. `GET user:1`이 LRU를 갱신하므로 `user:3` 저장 시 `user:2`가 제거됩니다.
2. `GET user:2`는 `(nil)`, `GET user:1`은 `"Alice"`입니다.
3. `INFO memory`는 `used_memory:24`, `maxmemory:30`, `evicted_keys:1`을 출력합니다.
4. TTL 3초 후 `GET user:1`은 `(nil)`, `TTL user:1`은 -2입니다.
5. `user:3`까지 DEL하면 `DBSIZE`는 0입니다.
6. 제한을 5로 바꾼 뒤 큰 엔트리를 저장하면 OOM이 발생합니다.
7. 마지막 네 명령은 각각 이미 제거된 키, 잘못된 정수, 인자 부족, 알 수 없는 명령의 처리를 보여줍니다.

`KEYS`의 출력 순서는 평가 요구사항상 보장하지 않습니다. 키의 존재 여부만 확인하면 됩니다.

## 자주 나오는 질문에 대한 짧은 답변

### 해시맵과 이중 연결 리스트가 필요한 이유가 체이닝 때문인가요?

아닙니다. 체이닝은 해시맵 버킷 내부의 충돌 해결 방법입니다. 별도의 이중 연결 리스트는 전체 키의 LRU 순서를 관리합니다. 두 구조를 결합하는 이유는 키 조회와 최근 사용 갱신을 모두 평균 O(1)에 처리하기 위해서입니다.

### `Entry.lru_node`가 무엇인가요?

해시맵에서 찾은 Entry가 LRU 리스트 안에서 자신의 노드를 직접 가리키는 참조입니다. 이 값이 있기 때문에 리스트를 순회하지 않고 해당 노드를 바로 이동하거나 삭제할 수 있습니다.

### TTL과 LRU의 차이는 무엇인가요?

TTL은 정해진 만료 시간이 된 키를 삭제하고, LRU는 메모리가 부족할 때 가장 오래 사용하지 않은 키를 삭제합니다. TTL 삭제는 `evicted_keys`를 증가시키지 않지만 LRU 삭제는 증가시킵니다.

### 왜 만료 힙에서 임의 항목을 바로 삭제하지 않나요?

일반적인 이진 힙에서 키 하나의 임의 위치를 찾으려면 O(n)이 필요합니다. 그래서 TTL을 변경하거나 DEL할 때 예전 힙 레코드를 남겨두고, 루트에 도착했을 때 현재 Entry와 비교해 무시하는 lazy deletion을 선택했습니다.

### 시간 복잡도를 한 번에 정리하면?

| 기능 | 평균 시간 복잡도 |
|---|---:|
| 해시맵 조회·수정·삭제 | O(1) |
| LRU 노드 이동·삭제 | O(1) |
| TTL 힙 추가·삭제 | O(log n) |
| 다음 만료 확인 | O(1) |
| KEYS | O(n) |
| 해시맵 전체 리사이즈 | O(n), 삽입 전체로 보면 분할 상환 O(1) |

## 자동 검증

```bash
python -m unittest discover -v
```

테스트는 필수 명령, LRU, OOM, UTF-8 메모리, TTL 재설정, 오류 형식, 해시 충돌·확장, 힙, 이중 연결 리스트와 모든 보너스 기능을 검증합니다.

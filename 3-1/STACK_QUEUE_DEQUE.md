# 스택, 큐, 덱 정리

이 문서의 세 컬렉션은 `structures/linear_collections.py`에 구현되어 있습니다. 내장 `collections`는 사용하지 않고 과제에서 직접 만든 동적 배열과 이중 연결 리스트를 재사용합니다.

## Stack

스택은 마지막에 넣은 값을 먼저 꺼내는 LIFO(Last In, First Out) 구조입니다.

- 저장소: `DynamicArray`
- `push`: 배열 뒤에 추가, 분할 상환 O(1)
- `pop`: 배열의 마지막 슬롯 제거, O(1)
- `peek`: 마지막 값 확인, O(1)
- 활용: 실행 취소, 괄호 검사, DFS

## Queue

큐는 먼저 넣은 값을 먼저 꺼내는 FIFO(First In, First Out) 구조입니다.

- 저장소: `DoublyLinkedList`
- `enqueue`: 리스트 뒤에 추가, O(1)
- `dequeue`: 리스트 앞에서 제거, O(1)
- `peek`: 맨 앞 값 확인, O(1)
- 활용: 작업 스케줄링, BFS, Pub/Sub 구독자 메시지 버퍼

배열 앞에서 값을 제거하면 나머지를 이동해야 하므로 O(n)이 됩니다. 이 구현은 리스트의 `head`와 `tail`을 사용해 양쪽 연산을 O(1)로 유지합니다.

## Deque

덱은 앞과 뒤 양쪽에서 삽입과 삭제가 가능한 Double-Ended Queue입니다.

- 저장소: `DoublyLinkedList`
- `append_left`, `append_right`: O(1)
- `pop_left`, `pop_right`: O(1)
- `peek_left`, `peek_right`: O(1)
- 활용: 슬라이딩 윈도우, 양방향 탐색, 작업 훔치기 큐

## Mini Redis에서의 재사용

- LRU는 이중 연결 리스트를 덱처럼 사용합니다. 최신 항목은 앞, 제거 후보는 뒤입니다.
- Pub/Sub은 각 구독자에게 독립적인 `Queue`를 하나씩 두어 발행 순서대로 메시지를 꺼냅니다.
- TTL 최소 힙의 내부 저장소는 `DynamicArray`입니다.

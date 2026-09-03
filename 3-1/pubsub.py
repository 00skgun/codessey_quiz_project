"""연결 리스트와 큐를 재사용한 간단한 채널 기반 Pub/Sub."""

from typing import Optional

from structures.doubly_linked_list import DoublyLinkedList
from structures.hash_map import HashMap
from structures.linear_collections import Queue


class Subscription:
    __slots__ = ("subscriber_id", "messages")

    def __init__(self, subscriber_id: str) -> None:
        self.subscriber_id = subscriber_id
        self.messages = Queue()


class Channel:
    def __init__(self) -> None:
        self.subscriptions = DoublyLinkedList()

    def find(self, subscriber_id: str) -> Optional[Subscription]:
        for subscription in self.subscriptions.iter_front():
            if subscription.subscriber_id == subscriber_id:
                return subscription
        return None


class PubSubBroker:
    """각 구독자에게 독립 메시지 큐를 제공한다."""

    def __init__(self) -> None:
        self._channels = HashMap()

    def subscribe(self, channel_name: str, subscriber_id: str) -> int:
        channel = self._channels.get(channel_name)
        if channel is None:
            channel = Channel()
            self._channels.put(channel_name, channel)
        if channel.find(subscriber_id) is None:
            channel.subscriptions.insert_back(Subscription(subscriber_id))
        return channel.subscriptions.size()

    def publish(self, channel_name: str, message: str) -> int:
        channel = self._channels.get(channel_name)
        if channel is None:
            return 0
        delivered = 0
        for subscription in channel.subscriptions.iter_front():
            subscription.messages.enqueue(message)
            delivered += 1
        return delivered

    def poll(self, channel_name: str, subscriber_id: str) -> Optional[str]:
        channel = self._channels.get(channel_name)
        if channel is None:
            return None
        subscription = channel.find(subscriber_id)
        if subscription is None:
            return None
        return subscription.messages.dequeue()

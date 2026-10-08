import os
import string
import random

from aiokafka import AIOKafkaProducer

from common import TOPIC_NAME, Message, kafka_servers


class Producer:

    MAX_MESSAGE_LENGTH = 100

    def __init__(self, producer: AIOKafkaProducer | None = None) -> None:
        self.producer = producer or AIOKafkaProducer(bootstrap_servers=kafka_servers())

    async def start(self) -> None:
        await self.producer.start()

    async def stop(self) -> None:
        await self.producer.stop()

    async def run(self, num_messages: int = 1000) -> None:
        for _ in range(num_messages):
            characters = string.ascii_letters + string.digits
            length = random.randint(1, self.MAX_MESSAGE_LENGTH)
            content = ''.join(random.choices(characters, k=length))
            message = Message(content=content)
            await self.producer.send(TOPIC_NAME, message.serialize())
        await self.producer.flush()

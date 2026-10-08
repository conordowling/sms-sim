import asyncio
import os
import random
import time

from aiokafka import AIOKafkaConsumer
from aiokafka.structs import ConsumerRecord

from common import TOPIC_NAME, Message, MessageResult, kafka_servers
from message_record_service import MessageRecordService


class Sender:

    GROUP_ID = "sms_sender"
    BATCH_SIZE = 10
    POLL_TIMEOUT_MS = 1000

    def __init__(
        self,
        mean_send_time_seconds: float,
        failure_rate: float,
    ):
        self.mean_send_time_seconds = mean_send_time_seconds
        self.failure_rate = failure_rate
        self.record_service = MessageRecordService()

    async def run(self):
        consumer = AIOKafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=kafka_servers(),
            group_id=self.GROUP_ID,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        await self.record_service.open()
        await consumer.start()
        try:
            while True:
                records = await consumer.getmany(timeout_ms=self.POLL_TIMEOUT_MS, max_records=self.BATCH_SIZE)
                batch = [record for records_for_partition in records.values() for record in records_for_partition]
                if not batch:
                    continue

                sem = asyncio.Semaphore(5)  # Just choosing a number < BATCH_SIZE
                results = await asyncio.gather(*(self._send_message(sem, msg) for msg in batch))
                await self.record_service.record_batch(list(results))
                await consumer.commit()
        finally:
            await self.record_service.close()
            await consumer.stop()


    async def _send_message(self, sem: asyncio.Semaphore, msg: ConsumerRecord) -> MessageResult:
        async with sem:
            message = Message.deserialize(msg.value)

            # This implementation does not retry on failures because that seemed like part of the requirements, but if we
            # wanted to decrease the failure rate (assuming failures are unrelated to the contents of the message) we could
            # add a retry policy. We also drop the records on the floor if they fail, but if we needed to re-process them,
            # we could use a dead letter queue.
            is_fail = random.random() < self.failure_rate

            # uses a uniform distribution to generate a wait time with the prescribed mean. We could potentially use a
            # different statistical distribution for the purposes of the simulation.
            wait_time = random.random() * (2 * self.mean_send_time_seconds)

            await asyncio.sleep(wait_time)

            return MessageResult(
                success=not is_fail,
                send_time=wait_time,
                content=message.content,
                timestamp=time.time(),
            )


if __name__ == "__main__":
    mean_send_time_seconds = float(os.environ.get("MEAN_SEND_TIME_SECONDS", "0.1"))
    failure_rate = float(os.environ.get("FAILURE_RATE", "0.05"))
    sender = Sender(mean_send_time_seconds=mean_send_time_seconds, failure_rate=failure_rate)
    asyncio.run(sender.run())

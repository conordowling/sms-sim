from unittest.mock import AsyncMock

from common import Message
from producer import Producer


async def test_run_sends_exactly_num_messages():
    """Asserts that the producer class sends exactly the expected number of messages to Kafka."""
    producer = Producer(producer=AsyncMock())
    await producer.run(num_messages=37)
    assert producer.producer.send.await_count == 37


async def test_run_messages_never_exceed_max_length():
    """Length is random per message, so check a large sample rather than
    a single message — large enough that an off-by-one in the bound
    (e.g. randint(1, MAX_MESSAGE_LENGTH + 1)) would almost certainly show
    up rather than slip through by chance."""
    producer = Producer(producer=AsyncMock())

    await producer.run(num_messages=1000)

    assert producer.producer.send.await_count == 1000
    for call in producer.producer.send.await_args_list:
        _, payload = call.args
        content = Message.deserialize(payload).content
        assert len(content) <= Producer.MAX_MESSAGE_LENGTH

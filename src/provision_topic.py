import asyncio
import os

from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError, for_code

from common import TOPIC_NAME, kafka_servers


async def provision_topic(num_partitions: int) -> None:
    """Create the topic with `num_partitions` partitions, matching the number of senders.
    """
    admin = AIOKafkaAdminClient(bootstrap_servers=kafka_servers())
    await admin.start()
    try:
        # create_topics doesn't raise on a per-topic conflict — it returns
        # a response with one (topic, error_code, error_message) per topic
        # requested, which has to be checked manually.
        response = await admin.create_topics(
            [NewTopic(TOPIC_NAME, num_partitions=num_partitions, replication_factor=1)]
        )
        for topic, error_code, error_message in response.topic_errors:
            if error_code == 0:
                print(f"created {TOPIC_NAME} with {num_partitions} partitions")
            elif for_code(error_code) is TopicAlreadyExistsError:
                print(f"{TOPIC_NAME} already exists, nothing to do")
            else:
                raise for_code(error_code)(error_message)
    finally:
        await admin.close()


if __name__ == "__main__":
    num_partitions = int(os.environ.get("SENDER_REPLICAS", "3"))
    asyncio.run(provision_topic(num_partitions))

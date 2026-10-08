import os
import json
from dataclasses import dataclass, asdict

TOPIC_NAME = "sms_messages"

@dataclass(frozen=True)
class Message:
    content: str


    def serialize(self) -> bytes:
        return json.dumps(asdict(self)).encode()

    @staticmethod
    def deserialize(data: bytes) -> Message:
        return Message(**json.loads(data.decode()))


@dataclass(frozen=True)
class MessageResult:
    success: bool
    send_time: float
    content: str
    timestamp: float


@dataclass(frozen=True)
class MessageStats:
    sent: int
    failed: int
    avg_send_time_seconds: float


def kafka_servers() -> list[str]:
    servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    return servers.split(",")


def get_dsn() -> str:
    """Database connection string."""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://sms:sms@localhost:5432/sms_simulation",
    )


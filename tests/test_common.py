import pytest

from common import Message


@pytest.mark.parametrize(
    "content",
    [
        "",
        "hello world",
        "unicode: café 中文 😀",
        'has "quotes" and \\backslashes\\',
    ],
    ids=["empty", "ascii", "unicode", "quotes-and-backslashes"],
)
def test_message_serialize_deserialize_roundtrip(content):
    message = Message(content=content)

    deserialized = Message.deserialize(message.serialize())

    assert deserialized == message
    assert deserialized.content == content

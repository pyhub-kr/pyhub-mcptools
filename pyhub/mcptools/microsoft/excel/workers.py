from channels.consumer import AsyncConsumer
from channels.layers import get_channel_layer


class DummyWorker(AsyncConsumer):
    # TODO: 이 설정을 강제할려면? asgi.py 내에서 참조
    channel_name = "excel-dummy"

    async def test_print(self, message: dict):
        text = message["text"]  # or keys: "type"
        print("Test: " + text)

    @classmethod
    async def send_test_print(cls, text: str) -> None:
        channel_layer = get_channel_layer("default")
        await channel_layer.send(cls.channel_name, {"type": "test.print", "text": text})

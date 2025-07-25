from channels.generic.websocket import AsyncWebsocketConsumer  #type: ignore
import json  #type: ignore
from channels.layers import get_channel_layer #type: ignore

from .views import start_recognition

channel_layer = get_channel_layer()

class AttendanceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(json.dumps({"message": "WebSocket Connected"}))

    async def disconnect(self, close_code):
        print("WebSocket Disconnected")

    async def receive(self, text_data):
        data = json.loads(text_data)
        class_name = data.get("class")
        message = start_recognition(class_name)

        # Send update to all clients
        await self.channel_layer.group_send(
            "attendance_updates", {"type": "send_update", "message": message}
        )

    async def send_update(self, event):
        await self.send(json.dumps({"message": event["message"]}))


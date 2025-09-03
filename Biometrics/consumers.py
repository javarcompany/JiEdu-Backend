from channels.generic.websocket import AsyncWebsocketConsumer  #type: ignore
import json  #type: ignore
from channels.layers import get_channel_layer #type: ignore

from .views import start_recognition

channel_layer = get_channel_layer()

class AttendanceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        lesson_id = self.scope['url_route']['kwargs']['lesson_id']
        self.group_name = f"lesson_{lesson_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()
        
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

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

    async def recognition_stopped(self, event):
        await self.send_json({
            "type": "recognition_stopped",
            "camera": event["camera"],
        })
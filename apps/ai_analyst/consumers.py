import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class AIChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer — AI bilan real-time chat."""

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or self.user.is_anonymous:
            await self.close()
            return
        await self.accept()
        await self.send(text_data=json.dumps({
            "type": "system",
            "message": "AI tahlilchi tayyor. Savolingizni yozing!"
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            question = data.get("message", "").strip()
            source = data.get("source", None)
            if source == 'all':
                source = None

            if not question:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Savol bo'sh bo'lmasligi kerak!"
                }))
                return

            # Typing indicator
            await self.send(text_data=json.dumps({
                "type": "typing",
                "message": "AI o'ylayapti..."
            }))

            # AI javobni streaming rejimda yuborish
            full_response = ""
            async for chunk in self._stream_response(question, source):
                full_response += chunk
                await self.send(text_data=json.dumps({
                    "type": "stream",
                    "chunk": chunk,
                }))

            # Yakuniy javob
            await self.send(text_data=json.dumps({
                "type": "message",
                "message": full_response,
            }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Noto'g'ri format!"
            }))
        except Exception as e:
            logger.error(f"AI Chat xatolik: {e}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": f"Xatolik: {str(e)}"
            }))

    async def _stream_response(self, question, source=None):
        """AI javobini streaming rejimda generatsiya qilish."""
        from .services import stream_analyze, get_context_data

        context_data = await sync_to_async(get_context_data)(source=source)

        # sync generator ni async ga o'tkazish
        import asyncio

        def _generate():
            return list(stream_analyze(question, context_data, source=source))

        chunks = await sync_to_async(_generate)()
        for chunk in chunks:
            yield chunk

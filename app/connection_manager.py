from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel_id: str):
        await websocket.accept()
        if channel_id not in self.active_connections:
            self.active_connections[channel_id] = []
        self.active_connections[channel_id].append(websocket)

    def disconnect(self, websocket: WebSocket, channel_id: str):
        self.active_connections[channel_id].remove(websocket)
        if not self.active_connections[channel_id]:
            self.active_connections.pop(channel_id)

    async def broadcast(self, message: str, channel_id: str):
        for connection in self.active_connections.get(channel_id, []):
            await connection.send_text(message)

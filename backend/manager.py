from __future__ import annotations

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[int, list[WebSocket]] = {}

    def connect(
        self,
        negotiation_id: int,
        websocket: WebSocket,
    ) -> None:
        self.active_connections.setdefault(
            negotiation_id,
            [],
        ).append(websocket)

    def disconnect(
        self,
        negotiation_id: int,
        websocket: WebSocket,
    ) -> None:
        connections = self.active_connections.get(
            negotiation_id,
            [],
        )

        if websocket in connections:
            connections.remove(websocket)

        if not connections:
            self.active_connections.pop(
                negotiation_id,
                None,
            )

    async def broadcast(
        self,
        negotiation_id: int,
        event: dict,
    ) -> None:
        connections = list(
            self.active_connections.get(
                negotiation_id,
                [],
            )
        )

        for websocket in connections:
            await websocket.send_json(event)


manager = ConnectionManager()
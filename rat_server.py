import asyncio
import websockets
import json
import os
import ssl
import pathlib

CONNECTED_CLIENTS = {}
CONNECTED_PANELS = []

async def broadcast_client_list():
    """Sends the current list of clients to all connected panels."""
    if not CONNECTED_PANELS: return
    client_list = {cid: {"hostname": info["hostname"]} for cid, info in CONNECTED_CLIENTS.items()}
    list_payload = json.dumps({"type": "client_list", "clients": client_list})
    panels = list(CONNECTED_PANELS)
    if panels: await asyncio.gather(*[panel.send(list_payload) for panel in panels])

async def handler(websocket, path):
    print(f"[*] New connection from {websocket.remote_address}")
    initial_data = None
    try:
        initial_message = await websocket.recv()
        initial_data = json.loads(initial_message)
        role = initial_data.get("role")

        if role == "panel":
            CONNECTED_PANELS.append(websocket)
            print(f"[*] Control Panel connected. Total panels: {len(CONNECTED_PANELS)}")
            await broadcast_client_list()
            # The panel will now listen for broadcasts and send targeted commands
            async for message in websocket:
                data = json.loads(message)
                target_id = data.get("target_id")
                if target_id and target_id in CONNECTED_CLIENTS:
                    await CONNECTED_CLIENTS[target_id]["ws"].send(json.dumps(data))

        elif role == "client":
            client_id = initial_data.get("id")
            hostname = initial_data.get("hostname", "Unknown")
            CONNECTED_CLIENTS[client_id] = {"ws": websocket, "hostname": hostname}
            print(f"[*] Client '{hostname}' ({client_id}) connected. Total clients: {len(CONNECTED_CLIENTS)}")
            await broadcast_client_list()
            # The client will stream screen data and listen for commands
            async for message in websocket:
                data = json.loads(message)
                payload = json.dumps({
                    "type": "screen_data", "session_id": client_id,
                    "data": data.get("data"), "width": data.get("width"), "height": data.get("height")
                })
                panels = list(CONNECTED_PANELS)
                if panels: await asyncio.gather(*[panel.send(payload) for panel in panels])
        else:
            await websocket.close(1011, "Unknown role provided.")

    except websockets.ConnectionClosed:
        print(f"[!] A connection closed.")
    finally:
        if initial_data:
            role = initial_data.get("role")
            if role == "panel" and websocket in CONNECTED_PANELS:
                CONNECTED_PANELS.remove(websocket)
                print("[*] Control Panel disconnected.")
            elif role == "client":
                client_id = initial_data.get("id")
                if client_id in CONNECTED_CLIENTS:
                    del CONNECTED_CLIENTS[client_id]
                    print(f"[*] Client '{client_id}' disconnected.")
                    await broadcast_client_list()

async def main():
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8765))
    print(f"[*] Starting plain WebSocket server on ws://{host}:{port}")
    async with websockets.serve(handler, host, port, max_size=None):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
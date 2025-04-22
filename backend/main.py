if __name__ == "__main__":
    from dotenv import load_dotenv, get_key
    from pathlib import Path
    import os
    import ssl
    import asyncio
    from server import Server
    load_dotenv()
    
    port = int(get_key(".env", "PORT"))
    host = get_key(".env", "URL")

    # Percorsi assoluti dei certificati
    _dirname = Path(__file__).parent
    root_dir = _dirname.parent
    certfile = root_dir / "certificate.crt"
    keyfile = root_dir / "private.key"

    # Genera i certificati se non esistono
    if not certfile.is_file() or not keyfile.is_file():
        print("Certificates not found. Generating new self-signed certificates...")
        os.system(f'openssl req -x509 -newkey rsa:4096 -keyout {keyfile} -out {certfile} -days 365 -nodes -subj "/CN=localhost"')

    # Creazione del contesto SSL
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        ssl_context.load_cert_chain(certfile=str(certfile), keyfile=str(keyfile))
        print("Certificate and key loaded successfully")
    except Exception as e:
        print(f"Error loading certificate: {e}")
        exit(1)

    # Creazione e avvio del server WebSocket
    server = Server(port, host, ssl_context)

    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        exit(-1)
    except Exception as e:
        raise
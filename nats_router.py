#!/usr/bin/env python3
"""
NATS Router for Apple Notes
Listens to messages.10.raw.type.applenotes and publishes to messages.20.applenotes
"""

import asyncio
import json
import os
import ssl
import sys
import uuid

import nats

NATS_URL = os.environ.get("NATS_URL")
if not NATS_URL:
    print("Error: NATS_URL environment variable not set")
    sys.exit(1)

CERTS_DIR = os.environ.get("CERTS_DIR", "/tmp/nats-certs")
INPUT_TOPIC = "messages.10.raw.type.applenotes"
OUTPUT_TOPIC = "messages.20.applenotes"


def _make_ssl_ctx() -> ssl.SSLContext:
    """Create SSL context with client certificate for mTLS."""
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cafile=f"{CERTS_DIR}/rootCA.pem")
    ctx.load_cert_chain(
        certfile=f"{CERTS_DIR}/client.pem",
        keyfile=f"{CERTS_DIR}/client.key"
    )
    return ctx


async def _connect_with_retry(url: str) -> nats.aio.client.Client:
    """Connect to NATS with retry logic and TLS."""
    ssl_ctx = _make_ssl_ctx()
    for attempt in range(5):
        try:
            return await nats.connect(url, tls=ssl_ctx, connect_timeout=2)
        except Exception as e:
            if attempt < 4:
                print(f"Connection attempt {attempt + 1}/5 failed, retrying in 1s...")
                await asyncio.sleep(1)
            else:
                print(f"Error: Could not connect to NATS at {url} after 5 attempts")
                print(f"Make sure NATS server is running: {e}")
                sys.exit(1)


async def route_apple_notes(input_msg: dict, client: nats.aio.client.Client) -> None:
    """Transform Apple Notes to messages.20.applenotes format."""
    original_note = input_msg.get("note", {})

    # Create standardized message format (matching Google Notes format)
    routed_message = {
        "id": input_msg.get("id", str(uuid.uuid4())),
        "message_type": "applenotes",
        "note": {
            "id": original_note.get("id", str(uuid.uuid4())),
            "title": original_note.get("title", "Untitled"),
            "text": original_note.get("text"),
            "url": original_note.get("url"),
            "date": input_msg.get("date"),
        },
        "source": "apple-notes"
    }

    await client.publish(OUTPUT_TOPIC, json.dumps(routed_message).encode())
    title = original_note.get("title", "Untitled")
    print(f"✓ Routed to messages.20.applenotes: {title}")


async def main() -> None:
    """Subscribe to messages.10.raw.type.applenotes and route to messages.20.applenotes."""
    nc = await _connect_with_retry(NATS_URL)

    print(f"🔄 Apple Notes Router started")
    print(f"  Input topic:  {INPUT_TOPIC}")
    print(f"  Output topic: {OUTPUT_TOPIC}")

    try:
        async def handler(msg):
            try:
                message_data = json.loads(msg.data.decode())
                await route_apple_notes(message_data, nc)
            except json.JSONDecodeError as e:
                print(f"✗ Failed to decode message: {e}")
            except Exception as e:
                print(f"✗ Error processing message: {e}")

        await nc.subscribe(INPUT_TOPIC, cb=handler)
        await asyncio.Future()  # run forever

    except KeyboardInterrupt:
        print("\n✓ Router stopped")
    finally:
        await nc.close()


if __name__ == "__main__":
    asyncio.run(main())

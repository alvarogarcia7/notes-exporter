#!/usr/bin/env python3
"""
NATS Publisher for Apple Notes exported via notes-exporter
Reads exported notes and publishes them to NATS
"""

import asyncio
import json
import os
import ssl
import sys
import uuid
import click
from pathlib import Path

import nats
from date_extractor import format_message_with_date

NATS_URL = os.environ.get("NATS_URL")
if not NATS_URL:
    print("Error: NATS_URL environment variable not set")
    sys.exit(1)
CERTS_DIR = os.environ.get("CERTS_DIR", "/tmp/nats-certs")
TOPIC = "messages.10.raw"


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


async def publish_notes(data_dir: str):
    """Publish all JSON notes from an Apple Notes export directory to NATS."""
    data_path = Path(data_dir)

    if not data_path.exists() or not data_path.is_dir():
        print(f"Error: Data directory '{data_dir}' does not exist")
        sys.exit(1)

    json_files = sorted(data_path.glob("*.json"))
    if not json_files:
        print(f"Warning: No JSON files found in '{data_dir}'")
        print(f"Make sure you have exported notes from Apple Notes using notes-exporter")
        return

    print(f"Found {len(json_files)} note(s) to publish from Apple Notes export")

    nc = await _connect_with_retry(NATS_URL)

    try:
        published_count = 0
        for json_file in json_files:
            try:
                with open(json_file) as f:
                    note_data = json.load(f)

                message = {
                    "id": str(uuid.uuid4()),
                    "source": "apple-notes",
                    "note": note_data,
                    "filename": json_file.name
                }

                # Add date field (with title override support)
                message = format_message_with_date(message, note_data)

                message_json = json.dumps(message)
                await nc.publish(TOPIC, message_json.encode())
                date_str = f" (date: {message['date']})" if message.get('date') else ""
                print(f"✓ Published {json_file.name} (note_id: {note_data.get('id', 'unknown')}){date_str}")
                published_count += 1
            except json.JSONDecodeError as e:
                print(f"✗ Failed to parse {json_file.name}: {e}")
            except Exception as e:
                print(f"✗ Failed to publish {json_file.name}: {e}")

        if published_count > 0:
            print(f"✓ Published {published_count}/{len(json_files)} note(s) to '{TOPIC}'")
        else:
            print(f"✗ No notes were successfully published")
            sys.exit(1)

    finally:
        await nc.close()


@click.command()
@click.option(
    '--data-dir',
    default='data',
    help='Data directory containing exported JSON note files (default: ./data)'
)
def main(data_dir: str):
    """
    Publish Apple Notes from notes-exporter to NATS.

    Notes should be exported from Apple Notes using notes-exporter first.
    The default data directory is './data' in the current directory.

    Example:
        python3 nats_publisher.py --data-dir ./AppleNotesExport/data
    """
    asyncio.run(publish_notes(data_dir))


if __name__ == "__main__":
    main()

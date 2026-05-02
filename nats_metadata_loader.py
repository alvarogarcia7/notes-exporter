#!/usr/bin/env python3
"""
NATS loader for Apple Notes metadata from iCloud-Notes.json.
Reads metadata entries and publishes to NATS for indexing and tracking.
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
from apple_notes_metadata_parser import load_apple_notes_metadata

NATS_URL = os.environ.get("NATS_URL")
if not NATS_URL:
    print("Error: NATS_URL environment variable not set")
    sys.exit(1)
CERTS_DIR = os.environ.get("CERTS_DIR", "/tmp/nats-certs")
TOPIC = "messages.5.apple-notes-metadata"  # Metadata topic


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


async def load_metadata(metadata_file: str):
    """Load and publish Apple Notes metadata from iCloud-Notes.json."""
    metadata_path = Path(metadata_file)

    if not metadata_path.exists():
        print(f"Error: Metadata file '{metadata_file}' does not exist")
        sys.exit(1)

    print(f"Loading Apple Notes metadata from: {metadata_file}")

    # Load JSON file
    try:
        with open(metadata_path) as f:
            json_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to read file: {e}")
        sys.exit(1)

    # Parse metadata
    print("Parsing metadata entries...")
    try:
        parsed_metadata = load_apple_notes_metadata(json_data)
    except Exception as e:
        print(f"Error: Failed to parse metadata: {e}")
        sys.exit(1)

    if not parsed_metadata:
        print("Warning: No metadata entries found")
        return

    print(f"Found {len(parsed_metadata)} metadata entries")

    # Connect to NATS
    nc = await _connect_with_retry(NATS_URL)

    try:
        published_count = 0
        failed_count = 0

        for entry_id, parsed_data in parsed_metadata.items():
            try:
                # Create message
                message = {
                    "id": str(uuid.uuid4()),
                    "source": "apple-notes-metadata",
                    "entry_id": entry_id,
                    "note_id": parsed_data["note_id"],
                    "filename": parsed_data["filename"],
                    "created": parsed_data["created"],
                    "created_date": parsed_data["created_date_only"],
                    "modified": parsed_data["modified"],
                    "modified_date": parsed_data["modified_date_only"],
                    "first_exported": parsed_data["first_exported"],
                    "last_exported": parsed_data["last_exported"],
                    "export_count": parsed_data["export_count"],
                }

                # Publish to NATS
                message_json = json.dumps(message)
                await nc.publish(TOPIC, message_json.encode())

                date_str = f" (created: {parsed_data['created_date_only']})" if parsed_data.get('created_date_only') else ""
                print(f"✓ Published metadata for {parsed_data['filename']}{date_str}")
                published_count += 1

            except Exception as e:
                print(f"✗ Failed to publish metadata for entry {entry_id}: {e}")
                failed_count += 1

        # Summary
        print(f"")
        if published_count > 0:
            print(f"✓ Published {published_count}/{len(parsed_metadata)} metadata entries to '{TOPIC}'")
        if failed_count > 0:
            print(f"✗ Failed to publish {failed_count} entries")

    finally:
        await nc.close()


@click.command()
@click.option(
    '--metadata-file',
    default='AppleNotesExport/data/iCloud-Notes.json',
    help='Path to iCloud-Notes.json metadata file'
)
def main(metadata_file: str):
    """
    Load Apple Notes metadata from iCloud-Notes.json into NATS.

    This loader reads the Apple Notes export metadata file and publishes
    parsed metadata entries to NATS for indexing and tracking.

    Extracted fields:
    - Note ID (from fullNoteId CoreData URL)
    - Created date (converted from Apple format to ISO 8601)
    - Modified date (converted from Apple format to ISO 8601)
    - Export counts and timestamps
    - Filename

    Example:
        python3 nats_metadata_loader.py --metadata-file AppleNotesExport/data/iCloud-Notes.json
    """
    asyncio.run(load_metadata(metadata_file))


if __name__ == "__main__":
    main()

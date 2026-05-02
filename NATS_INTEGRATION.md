# Apple Notes → NATS Integration

This directory contains the notes-exporter tool plus a NATS publisher that integrates Apple Notes into the NATS pipeline.

## Overview

Apple Notes can now be published to the NATS message broker and processed alongside Google Keep notes. This enables:

1. **Unified note processing** — Both Apple Notes and Google Keep notes flow through the same parser system
2. **Automatic extraction** — Notes are parsed for time entries, training sessions, and action items
3. **NATS-based distribution** — Notes are published to `messages.10.raw` topic for consumption by listeners

## Workflow

```
Apple Notes (macOS)
       ↓
exportnotes.zsh (export to JSON)
       ↓
./data/ directory
       ↓
nats_publisher.py (publish to NATS)
       ↓
messages.10.raw (NATS topic)
       ↓
Parsers (time-entry, training, next-entry)
       ↓
/tmp/time-entries/, /tmp/training/, /tmp/next-entries/
```

## Setup

### 1. Export Notes from Apple Notes

Run the notes-exporter export script on macOS:

```bash
cd notes-exporter
./exportnotes.zsh
```

This creates an `AppleNotesExport/` directory (or similar) with your notes in JSON format.

**Option A: Use default data directory**

```bash
# Copy/link notes to ./data/
cp AppleNotesExport/data/*.json ./data/
```

**Option B: Point to export directory**

```bash
# Run with custom data directory
python3 nats_publisher.py --data-dir ~/Downloads/AppleNotesExport/data
```

### 2. Set Environment Variables

Ensure NATS is properly configured:

```bash
# From parent directory
source .env
# Or set manually:
export NATS_URL="tls://docker:4222"
export CERTS_DIR="/path/to/nats/certs"
```

### 3. Start the Publisher

**Option A: Direct execution**

```bash
# From notes-exporter directory
python3 nats_publisher.py --data-dir ./data
```

**Option B: Via bin/start.sh**

```bash
bash bin/start.sh
```

**Option C: Via Makefile (from parent directory)**

```bash
make notes-exporter-publisher
```

**Option D: Start entire system with publisher**

```bash
# Start NATS + all parsers + both publishers (Google Keep + Apple Notes)
make up
```

## File Format

Exported notes should be JSON files in the `data/` directory. Example structure:

```json
{
  "id": "note-123",
  "title": "Team Meeting Notes",
  "content": "Discussed Q2 planning...",
  "created": "2026-05-02T10:30:00Z",
  "modified": "2026-05-02T14:45:00Z",
  "tags": ["meeting", "planning"]
}
```

Each note is wrapped before publishing:

```json
{
  "id": "uuid-generated",
  "source": "apple-notes",
  "filename": "note-123.json",
  "note": {
    "id": "note-123",
    "title": "Team Meeting Notes",
    ...
  }
}
```

## Integration with Parsers

Published notes are automatically processed by:

1. **Time Entry Parser** — Extracts time logged from notes
   - Recognizes patterns like "2h meeting" or "spent 30 min on task"
   - Output: `/tmp/time-entries/`

2. **Training Parser** — Extracts training/learning sessions
   - Recognizes patterns like "Training: React Hooks" or "Learned X"
   - Output: `/tmp/training/`

3. **Next Entry Parser** — Extracts action items and tasks
   - Recognizes patterns like "TODO:" or "Next:"
   - Output: `/tmp/next-entries/`

## Usage Examples

### Basic Export and Publish

```bash
# 1. Export notes from Apple Notes
cd notes-exporter
./exportnotes.zsh

# 2. Publish to NATS
python3 nats_publisher.py --data-dir AppleNotesExport/data
```

### System-wide Integration

```bash
# 1. Setup system
make install

# 2. Start everything (both publishers + parsers)
make up

# 3. Check status
make status

# 4. View results
ls /tmp/time-entries/
ls /tmp/training/
ls /tmp/next-entries/
```

### Selective Publishing

```bash
# Start only Apple Notes publisher (assuming Google Keep not running)
make notes-exporter-publisher

# Start only Google Keep publisher
make publisher

# Start both
make up
```

### Continuous Publishing

For automated periodic export and publishing:

```bash
# 1. Set up launchd task (macOS)
python3 setup_launchd.py

# 2. Configure to run exportnotes.zsh periodically
# (See notes-exporter documentation for details)

# 3. Then run publisher in background
python3 nats_publisher.py --data-dir data &
```

## Troubleshooting

### No notes found

```
Error: No JSON files found in './data'
```

**Solution:** Ensure notes were exported first:
```bash
./exportnotes.zsh
cp AppleNotesExport/data/*.json ./data/
```

### NATS connection fails

```
Error: Could not connect to NATS at tls://docker:4222 after 5 attempts
```

**Solution:** Start NATS server:
```bash
make nats-up
# Or check if already running:
make nats-status
```

### Invalid certificate

```
ssl.SSLError: [SSL] certificate verify failed
```

**Solution:** Ensure certificates exist and CERTS_DIR is correct:
```bash
ls $CERTS_DIR/rootCA.pem
ls $CERTS_DIR/client.pem
# If missing, regenerate:
bash nats/gen-certs.sh
```

### Python dependencies

```
ModuleNotFoundError: No module named 'nats'
```

**Solution:** Install dependencies:
```bash
python3 -m pip install nats-py click
```

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `NATS_URL` | `tls://docker:4222` | NATS server URL |
| `CERTS_DIR` | `../nats/certs` | TLS certificate directory |
| `NOTES_EXPORT_DATA_DIR` | `./data` | Notes export data directory |

Set in `.env.sample` (copy to `.env`):

```bash
cp .env.sample .env
# Edit .env with your values
```

### Data Directory Structure

```
data/
├── note-1.json
├── note-2.json
├── note-3.json
└── (all notes from Apple Notes export)
```

## Performance

- **Publishing rate:** ~100 notes/second to NATS
- **Parsing time:** Depends on note size and parser complexity
- **Disk output:** Results written to `/tmp/*/` directories

## Limitations

- **macOS only:** Notes export requires macOS with Apple Notes app
- **Manual export:** Notes must be manually exported from Apple Notes (no API access)
- **JSON only:** Currently supports JSON export format from notes-exporter

## Future Enhancements

- [ ] Automated periodic export via launchd/cron
- [ ] Support for markdown export format
- [ ] Incremental sync (only export new/modified notes)
- [ ] Direct AppleScript integration without file staging
- [ ] Filtering by tag, folder, or date range

## See Also

- [notes-exporter README](./README.md) — Full notes-exporter documentation
- [NATS Infrastructure](../nats/README.md) — NATS server setup
- [Parser Documentation](../MAKEFILE.md) — System architecture

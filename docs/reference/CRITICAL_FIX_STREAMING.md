# CRITICAL FIX: Pipeline Event Streaming

## Problem Identified

**"Not all panels/processes are streaming their actions live"**

### Root Cause

The pipeline stages were **NOT emitting events** to the stream:

- ✅ `main.py` - Was emitting events
- ❌ `parsing/stages.py` - No events
- ❌ `embedding.py` - No events
- ❌ `intake/routes.py` - Only audit events, no pipeline events
- ❌ `multimodal/*.py` - No events

## Fixes Applied

### 1. Parsing Stages (`pipeline/pipeline/parsing/stages.py`)

Added event publishing at key points:

- Parse started
- Partition complete (element count)
- Chunking complete (chunk count)
- Parse complete (stats)
- Error events

### 2. Embedding Service (`pipeline/pipeline/embedding.py`)

Added event publishing:

- Embedding started
- Success/failure events

### 3. Intake Routes (`pipeline/pipeline/intake/routes.py`)

Added pipeline events:

- Batch received
- File stored to MinIO
- Batch completion

### 4. Image Processor (`pipeline/pipeline/multimodal/image_processor.py`)

Added events for:

- Processing started
- OCR running
- CLIP embedding
- Complete/error events

### 5. Document Upload Component

Created `DocumentUpload.tsx` - A working drag-and-drop upload component.

## How to Test

### 1. Verify Pipeline is Running

```bash
make pipeline-status
```

### 2. Test Event Stream

```bash
./scripts/test-event-stream.sh
```

### 3. Upload a Document

**Via Dashboard:**

1. Go to `/documents`
2. Use the "UPLOAD DOCUMENT" panel
3. Drop a file or click to select

**Via curl:**

```bash
curl -X POST http://localhost:8000/api/v1/intake \
  -F "file=@/path/to/document.pdf" \
  -F "tenant_id=default"
```

### 4. Watch Events Flow

You should see events in the **Pipeline Log** panel:

```
[INTAKE]  File received: document.pdf
[INTAKE]  Stored to MinIO: default/xxx/document.pdf
[PARSE]   Starting parse of document.pdf
[PARSE]   Partitioned document.pdf into 42 elements
[PARSE]   Chunked into 8 chunks
[PARSE]   Parse complete: 8 chunks, 1543 chars, 2 tables
[EMBED]   Starting embedding for: chunk-1...
[EMBED]   Generated 768d embedding
[VECTOR]  Upserted to Qdrant collection tenant_default
```

## Expected Behavior

### Live Streaming

- All pipeline stages emit events
- Events appear in real-time in Pipeline Log
- Model Activity Monitor shows live events
- No "DISCONNECTED" status when pipeline is running

### Upload Flow

```
User uploads file
    ↓
[INTAKE] File received
    ↓
[INTAKE] Stored to MinIO
    ↓
[PARSE] Parse started
    ↓
[PARSE] Partition → Chunk
    ↓
[PARSE] Parse complete
    ↓
[EMBED] Generate embeddings
    ↓
[VECTOR] Store in Qdrant
    ↓
[METADATA] Index complete
```

## Troubleshooting

### No events appearing

```bash
# Check services
make pipeline-status

# Check pipeline logs
make pipeline-logs

# Test Redis
redis-cli ping

# Test SSE endpoint
curl -N http://localhost:8000/api/v1/pipeline/stream
```

### Upload fails

1. Check file size (max?)
2. Check file type (PDF, DOCX, TXT supported)
3. Check browser console for CORS errors
4. Verify `tenant_id` is correct

### Events stop after INTAKE

- Parsing/embedding workers may not be running
- Check for errors in pipeline logs
- Verify all Python dependencies installed

## Files Changed

### Backend

- `pipeline/pipeline/parsing/stages.py` - Added events
- `pipeline/pipeline/embedding.py` - Added events
- `pipeline/pipeline/intake/routes.py` - Added events
- `pipeline/pipeline/multimodal/image_processor.py` - Added events

### Frontend

- `packages/admin-dashboard/src/components/DocumentUpload.tsx` - NEW
- `packages/admin-dashboard/src/pages/DocumentList.tsx` - Added upload

### Scripts

- `scripts/test-event-stream.sh` - NEW

## Verification Checklist

- [ ] Pipeline API running on port 8000
- [ ] Redis running on port 6379
- [ ] Upload a document via dashboard
- [ ] See INTAKE event in Pipeline Log
- [ ] See PARSE events
- [ ] See EMBED events
- [ ] See VECTOR events
- [ ] Document appears in Document Queue
- [ ] Model Activity Monitor shows events

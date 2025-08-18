# Raw Documents

This directory contains incoming unprocessed documents in their original format.

## Purpose
- Initial landing zone for all documents entering the pipeline
- Preserves original document format and metadata
- No transformations or processing applied

## Document Types
- Email messages (.eml, .msg)
- PDF documents (.pdf)
- Audio/video files (.mp3, .mp4, .wav)
- Text documents (.txt, .md, .doc)
- Images (.jpg, .png, .tiff)

## Lifecycle
1. Documents arrive here from various sources (Gmail API, file upload, etc.)
2. Each document gets a unique pipeline_id
3. Original file is preserved with .meta.json metadata file
4. Documents move to `/staged/` when ready for processing

## Metadata Structure
Each document has an accompanying `.meta.json` file:
```json
{
  "pipeline_id": "unique-uuid",
  "source": "gmail|pdf|upload|transcription",
  "received_at": "2025-08-16T12:00:00Z",
  "original_filename": "document.pdf",
  "status": "raw",
  "content_type": "application/pdf",
  "size_bytes": 1024000
}
```

## Retention Policy
- Documents remain here until successfully processed
- Failed documents are moved to `/quarantine/`
- Successfully processed documents can be archived or deleted based on configuration
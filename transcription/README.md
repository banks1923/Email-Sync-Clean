# Transcription Service Documentation

## Overview

The Transcription Service provides audio and video transcription capabilities using OpenAI's Whisper model. It features confidence scoring, audio validation, and seamless integration with the Email Sync search system.

## Architecture

The service follows CLAUDE.md principles with a clean, flat architecture:

```
transcription/
├── main.py                    # Main service orchestration (254 lines)
├── providers/
│   └── whisper_provider.py    # Whisper integration (157 lines)
└── README.md                   # This documentation
```

## Features

### Core Capabilities
- **Audio/Video Transcription**: Supports MP3, MP4, WAV, M4A, WEBM, MOV, AVI formats
- **Confidence Scoring**: Uses avg_logprob for accurate quality assessment
- **Audio Validation**: Pre-flight checks using librosa for RMS energy and duration
- **Segment Timestamps**: Precise start/end times for timeline features
- **Batch Processing**: Transcribe multiple files efficiently
- **Database Integration**: Automatic storage in searchable database

### Quality Enhancements (Jan 2025)
- **Improved Confidence**: avg_logprob provides more reliable scores than no_speech_prob
- **Actual Duration**: Calculated from segment timestamps, not estimates
- **Audio Quality Checks**: RMS energy validation prevents processing silent/corrupt files
- **Metadata Storage**: Comprehensive metadata for filtering and analysis

## Installation

```bash
# Install required dependencies
pip install openai-whisper librosa

# Optional: Install specific Whisper model
# Models: tiny, base, small, medium, large
python -c "import whisper; whisper.load_model('base')"
```

## Usage

### Basic Transcription

```python
from transcription.main import TranscriptionService

# Initialize service
service = TranscriptionService()

# Transcribe single file
result = service.transcribe_file("audio.mp4")
if result["success"]:
    print(f"Text: {result['data']['text']}")
    print(f"Confidence: {result['data']['avg_confidence']}")
    print(f"Duration: {result['data']['duration']}s")
```

### Audio Validation

```python
from transcription.providers.whisper_provider import WhisperProvider

provider = WhisperProvider()

# Validate audio before transcription
validation = provider.validate_audio("audio.mp4")
if validation["valid"]:
    print(f"Audio is valid: {validation['duration']}s, RMS: {validation['rms_energy']}")
else:
    print("Audio quality too low or file too short")
```

### Batch Processing

```python
# Process multiple files
files = ["audio1.mp4", "audio2.mp3", "audio3.wav"]
results = service.transcribe_batch(files)

print(f"Processed: {results['data']['successful']} of {results['data']['total_files']}")
```

### Process Uploads Directory

```python
# Automatically process and move completed files
results = service.process_uploads_directory(
    input_dir="data/Uploads/Videos",
    output_dir="data/Output/Processed"
)

print(f"Successful: {results['metadata']['successful']}")
print(f"Failed: {results['metadata']['failed']}")
```

### Service Statistics

```python
# Get service status and metrics
stats = service.get_service_stats()

print(f"Status: {stats['data']['status']}")
print(f"Transcripts in DB: {stats['data']['transcripts_in_database']}")
print(f"Session stats: {stats['data']['session_stats']}")
```

## CLI Integration

```bash
# Single file transcription
scripts/vsearch transcribe audio.mp4

# Batch processing with limit
scripts/vsearch transcribe-batch videos/ -n 10

# Service statistics
scripts/vsearch transcription-stats
```

## Configuration

### Model Selection

```python
# Use different Whisper models
# tiny: Fastest, least accurate (39M parameters)
# base: Good balance (74M parameters) - DEFAULT
# small: Better accuracy (244M parameters)
# medium: High accuracy (769M parameters)
# large: Best accuracy (1550M parameters)

provider = WhisperProvider(model_name="small")
service = TranscriptionService()
service.provider = provider
```

### Confidence Thresholds

Confidence scores (avg_logprob) typically range from 0 to -2:
- **> -0.3**: Excellent quality
- **-0.3 to -0.7**: Good quality
- **-0.7 to -1.0**: Acceptable quality
- **< -1.0**: Poor quality (consider re-recording)

## Database Schema

Transcripts are stored in the `content` table with:

```json
{
  "content_type": "transcript",
  "title": "Audio: filename.mp4",
  "content": "Full transcription text...",
  "metadata": {
    "filename": "filename.mp4",
    "confidence": -0.45,
    "duration": 120.5,
    "engine": "whisper_base",
    "segments": 25,
    "language": "en"
  }
}
```

## Testing

### Run All Tests

```bash
# Run complete test suite
pytest tests/transcription_service/ -v

# Run with coverage
pytest tests/transcription_service/ --cov=transcription --cov-report=html
```

### Test Files

- `test_whisper_provider.py`: Provider unit tests
- `test_transcription_service.py`: Service orchestration tests
- `test_integration.py`: End-to-end integration tests

### Quick Test

```python
# Test service initialization
from transcription.main import TranscriptionService
service = TranscriptionService()
print(service.provider.is_available())  # Should print True

# Test audio validation
from transcription.providers.whisper_provider import WhisperProvider
provider = WhisperProvider()
result = provider.validate_audio("test.mp4")
print(result)
```

## Performance Considerations

### Memory Usage
- **tiny**: ~39MB model + ~100MB runtime
- **base**: ~74MB model + ~150MB runtime
- **small**: ~244MB model + ~300MB runtime
- **medium**: ~769MB model + ~800MB runtime
- **large**: ~1550MB model + ~2GB runtime

### Processing Speed (on M1 Mac)
- **tiny**: ~10x realtime
- **base**: ~7x realtime
- **small**: ~4x realtime
- **medium**: ~2x realtime
- **large**: ~1x realtime

### Optimization Tips
1. Use `base` model for general transcription
2. Process files under 30 minutes for best results
3. Batch process during off-peak hours
4. Monitor confidence scores for quality control
5. Pre-validate audio to avoid wasted processing

## Error Handling

The service handles various error conditions:

1. **Missing Dependencies**: Clear error message with installation instructions
2. **Invalid Files**: Validation before processing
3. **Transcription Failures**: Logged with detailed error messages
4. **Database Errors**: Graceful fallback with error reporting
5. **Low Quality Audio**: Detected via RMS energy validation

## API Reference

### TranscriptionService

**Methods:**
- `transcribe_file(file_path: str) -> Dict[str, Any]`
- `transcribe_batch(file_paths: List[str]) -> Dict[str, Any]`
- `process_uploads_directory(input_dir: str, output_dir: str) -> Dict[str, Any]`
- `get_service_stats() -> Dict[str, Any]`

### WhisperProvider

**Methods:**
- `__init__(model_name: str = "base")`
- `is_available() -> bool`
- `transcribe_file(file_path: str) -> Dict[str, Any]`
- `validate_audio(file_path: str) -> Dict[str, Any]`

## Integration with Email Sync

Transcriptions are automatically:
1. Stored in the unified content database
2. Indexed for full-text search
3. Available through the search API
4. Tagged with confidence metrics for quality filtering

## Troubleshooting

### Common Issues

**"Whisper not available"**
```bash
pip install openai-whisper
```

**"librosa not available"**
```bash
pip install librosa
```

**"Model not found"**
```python
import whisper
whisper.load_model("base")  # Downloads model if needed
```

**Low confidence scores**
- Check audio quality (background noise, volume)
- Try a larger model (small or medium)
- Ensure audio is clear and well-recorded

## Future Enhancements

Potential improvements aligned with CLAUDE.md principles:

1. **Speaker Diarization**: Identify different speakers
2. **Real-time Transcription**: Stream processing for live audio
3. **Language Detection**: Auto-detect and transcribe multiple languages
4. **Custom Vocabulary**: Domain-specific term recognition
5. **Confidence Filtering**: Auto-reject low-quality transcriptions

## Support

For issues or questions:
1. Check this documentation
2. Review test files for usage examples
3. Check logs in `logs/` directory
4. Verify dependencies with `provider.is_available()`

---

*Last Updated: January 2025*
*Follows CLAUDE.md architecture principles*

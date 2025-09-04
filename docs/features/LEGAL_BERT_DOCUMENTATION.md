# Legal BERT Integration Documentation

## Overview

This document provides comprehensive documentation for Legal BERT integration in the Email Sync system. Legal BERT is a specialized BERT model fine-tuned on legal documents, providing domain-specific embeddings for legal text analysis.

## Table of Contents

1. [Model Specifications](#model-specifications)
2. [Configuration](#configuration)
3. [Installation](#installation)
4. [Usage Examples](#usage-examples)
5. [API Reference](#api-reference)
6. [Architecture](#architecture)
7. [Performance Characteristics](#performance-characteristics)
8. [Troubleshooting](#troubleshooting)
9. [Migration Guide](#migration-guide)

## Model Specifications

### Legal BERT Model Details

- **Model Name**: `pile-of-law/legalbert-large-1.7M-2`
- **Architecture**: BERT-large (24 layers, 1024 hidden units, 16 attention heads)
- **Vocabulary Size**: 30,522 tokens
- **Max Sequence Length**: 512 tokens
- **Embedding Dimensions**: 1024 (fixed)
- **Training Data**: Legal documents, case law, contracts, regulations (1.7M legal documents)
- **Provider**: Pile of Law dataset with specialized legal training

### Technical Specifications

```python
# Model Constants (EmbeddingService class)
DEFAULT_MODEL_NAME = "pile-of-law/legalbert-large-1.7M-2"
EMBEDDING_DIMENSIONS = 1024  # Large model dimensions
MAX_SEQUENCE_LENGTH = 512  # BERT token limit

# New Clean Service Location
from embeddings import get_embedding_service
```

## Configuration

### Environment Variables

The new EmbeddingService automatically uses Legal BERT by default:

```bash
# No configuration needed - Legal BERT is the default
# The service automatically selects the best device (MPS/CUDA/CPU)

# Required: Model path (HuggingFace identifier or local path)
LEGAL_BERT_MODEL_PATH=pile-of-law/legalbert-large-1.7M-2

# Optional: Performance tuning
LEGAL_BERT_ENABLED=true                    # Enable/disable flag
LEGAL_BERT_BATCH_SIZE=32                   # Batch size (1-128)
LEGAL_BERT_MAX_LENGTH=512                  # Max token length (1-512)

# Optional: Dimension override (must be 1024 for Legal BERT Large)
EMBEDDING_DIMENSIONS=1024
```

### Configuration Validation

The system validates Legal BERT configuration through the `_validate_legal_bert()` method:

1. **Model Path Validation**: Ensures model path is provided and valid
2. **Dimension Validation**: Enforces 1024-dimensional embeddings
3. **Parameter Range Validation**: Validates batch size (1-128) and max length (1-512)
4. **Local Model Validation**: For local models, checks required files exist

### Provider Auto-Detection

The system automatically selects Legal BERT when:

```python
# Priority order for provider selection:
1. Explicit provider parameter: provider="legal_bert"
2. Environment variable: EMBEDDING_PROVIDER=legal_bert
3. Legal BERT config detected: LEGAL_BERT_MODEL_PATH set
4. OpenAI unavailable: Falls back to Legal BERT as free alternative
```

## Installation

### Option 1: Standard Installation

```bash
# Install required dependencies
pip install torch>=2.1.0 transformers>=4.41.0

# The model will be downloaded automatically on first use
```

### Option 2: Development Environment

```bash
# Install development dependencies (Legal BERT commented out by default)
pip install -r requirements-dev.txt

# Uncomment Legal BERT dependencies in requirements-dev.txt:
# torch>=2.1.0
# transformers>=4.41.0

# Then install:
pip install torch>=2.1.0 transformers>=4.41.0
```

### Option 3: Pre-download Model

```python
# Pre-download model to avoid first-run delay
from transformers import AutoModel, AutoTokenizer

model_name = "pile-of-law/legalbert-large-1.7M-2"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)
```

## Usage Examples

### Basic Usage

```python
from vector_service import VectorService
import os

# Configure for Legal BERT
os.environ["EMBEDDING_PROVIDER"] = "legal_bert"
os.environ["LEGAL_BERT_MODEL_PATH"] = "pile-of-law/legalbert-large-1.7M-2"

# Initialize service
service = VectorService()

# Check initialization
if service.validation_result["success"]:
    print(f"Initialized with: {service.embedding_provider}")
    print(f"Dimensions: {service.embedding_dimensions}")
else:
    print(f"Initialization failed: {service.validation_result['error']}")
```

### Direct Embedder Usage

```python
from vector_service.embeddings import EmbedderFactory
from vector_service.config import VectorConfig

# Create configuration
config = VectorConfig()

# Create Legal BERT embedder
result = EmbedderFactory.create_embedder(config, "legal_bert")

if result["success"]:
    embedder = result["embedder"]

    # Generate single embedding
    text = "This contract establishes the terms and conditions..."
    embedding_result = embedder.generate_embedding(text)

    if embedding_result["success"]:
        embedding = embedding_result["embedding"]  # List of 1024 floats
        print(f"Generated {len(embedding)} dimensional embedding")
        print(f"Model: {embedding_result['model']}")
    else:
        print(f"Embedding failed: {embedding_result['error']}")
else:
    print(f"Embedder creation failed: {result['error']}")
```

### Batch Processing

```python
# Process multiple legal documents
legal_texts = [
    "The plaintiff hereby agrees to the settlement terms...",
    "This confidentiality agreement binds all parties...",
    "The defendant's motion for summary judgment is denied...",
]

# Generate batch embeddings
batch_result = embedder.generate_batch_embeddings(legal_texts)

if batch_result["success"]:
    embeddings = batch_result["embeddings"]  # Dict mapping indices to embeddings
    print(f"Processed {batch_result['processed_count']} texts")
    print(f"Dimensions: {batch_result['dimensions']}")

    # Access individual embeddings
    for idx, embedding in embeddings.items():
        print(f"Text {idx}: {len(embedding)} dimensions")
else:
    print(f"Batch processing failed: {batch_result['error']}")
```

### Provider Comparison

```python
# Compare OpenAI vs Legal BERT embeddings
from vector_service.embeddings import EmbedderFactory
from vector_service.config import VectorConfig

config = VectorConfig()
legal_text = "The court hereby orders injunctive relief..."

# OpenAI embeddings
openai_result = EmbedderFactory.create_embedder(config, "openai")
if openai_result["success"]:
    openai_embedding = openai_result["embedder"].generate_embedding(legal_text)
    print(f"OpenAI: {openai_embedding.get('dimensions', 0)} dimensions")

# Legal BERT embeddings
legal_bert_result = EmbedderFactory.create_embedder(config, "legal_bert")
if legal_bert_result["success"]:
    legal_bert_embedding = legal_bert_result["embedder"].generate_embedding(legal_text)
    print(f"Legal BERT: {legal_bert_embedding.get('dimensions', 0)} dimensions")
```

## API Reference

### LegalBERTEmbedder Class

```python
class LegalBERTEmbedder(BaseEmbedder):
    """Legal BERT-based embedding generator."""

    # Class constants
    DEFAULT_MODEL_NAME = "nlpaueb/legal-bert-base-uncased"
    EMBEDDING_DIMENSIONS = 768
    MAX_SEQUENCE_LENGTH = 512
```

#### Methods

##### `__init__(config: Any) -> None`

Initialize Legal BERT embedder with configuration.

**Parameters:**
- `config`: VectorConfig with legal_bert_model_path (optional)

**Raises:**
- `ImportError`: If transformers/torch not available
- `ValueError`: If configuration invalid
- `RuntimeError`: If model loading fails

##### `generate_embedding(text: str) -> Dict[str, Any]`

Generate single embedding for given text.

**Parameters:**
- `text`: Input text to embed

**Returns:**
```python
# Success
{
    "success": True,
    "embedding": List[float],  # 1024 dimensions
    "model": str,              # Model name
    "dimensions": int,         # 1024
    "token_usage": None        # Not applicable for local models
}

# Error
{
    "success": False,
    "error": str
}
```

##### `generate_batch_embeddings(texts: List[str]) -> Dict[str, Any]`

Generate embeddings for multiple texts efficiently.

**Parameters:**
- `texts`: List of texts to embed

**Returns:**
```python
# Success
{
    "success": True,
    "embeddings": Dict[int, List[float]],  # Index -> 1024-dim embedding mapping
    "model": str,
    "dimensions": int,        # 1024
    "processed_count": int,
    "total_tokens": None      # Not applicable
}

# Error
{
    "success": False,
    "error": str
}
```

##### `get_embedding_dimensions() -> int`

Returns: `1024` (Legal BERT Large fixed dimensions)

##### `estimate_cost(text_list: List[str]) -> Dict[str, Any]`

Estimate processing cost (free for local models).

**Returns:**
```python
{
    "estimated_tokens": int,
    "estimated_cost_usd": 0.0,        # Free for local models
    "model": str,
    "texts_count": int,
    "cost_model": "local_inference"
}
```

### EmbedderFactory Integration

```python
# Provider registry includes Legal BERT
EmbedderFactory.PROVIDERS = {
    "openai": OpenAIEmbedder,
    "legal_bert": LegalBERTEmbedder,
    "legal-bert": LegalBERTEmbedder,              # Alternative naming
    "pile-of-law/legalbert-large-1.7M-2": LegalBERTEmbedder  # HuggingFace naming
}

# Provider capabilities
EmbedderFactory.PROVIDER_INFO = {
    "legal_bert": {
        "dimensions": [1024],
        "default_dimensions": 1024,
        "requires_api_key": False,
        "cost_per_1k_tokens": 0.0,
        "local_model": True
    }
}
```

## Architecture

### Class Hierarchy

```
BaseEmbedder (ABC)
 OpenAIEmbedder (formerly EmailEmbedder)
 LegalBERTEmbedder

EmbedderFactory
 Provider registry and capabilities
 Configuration validation
 Instance creation with error handling
```

### Integration Points

1. **VectorService**: Uses EmbedderFactory for provider creation
2. **VectorConfig**: Provides Legal BERT configuration validation
3. **Backward Compatibility**: EmailEmbedder alias preserved

### Device Support

Legal BERT automatically detects and uses optimal device:

```python
def _get_device(self) -> str:
    if torch.cuda.is_available():
        return "cuda"              # NVIDIA GPU
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return "mps"               # Apple Silicon GPU
    else:
        return "cpu"               # CPU fallback
```

## Performance Characteristics

### Embedding Generation Speed

| Batch Size | Device | Approximate Speed |
|------------|--------|-------------------|
| 1 text     | CPU    | ~100ms           |
| 1 text     | GPU    | ~50ms            |
| 32 texts   | CPU    | ~2-3 seconds     |
| 32 texts   | GPU    | ~500ms           |

### Memory Usage

| Component | CPU | GPU (CUDA/MPS) |
|-----------|-----|----------------|
| Model     | ~1.2GB | ~1.2GB        |
| Tokenizer | ~1MB   | ~1MB          |
| Per batch | ~50MB  | Variable      |

### Model Download Size

- **Initial download**: ~1.2GB (large model weights + tokenizer)
- **Cached location**: `~/.cache/huggingface/transformers/`
- **Network requirement**: Only for first use

## Troubleshooting

### Common Issues

#### 1. Import Errors

```python
ImportError: transformers and torch libraries required for Legal BERT.
```

**Solution:**
```bash
pip install torch>=2.1.0 transformers>=4.41.0
```

#### 2. Model Download Fails

```python
RuntimeError: Failed to load Legal BERT model: Connection error
```

**Solutions:**
- Check internet connection
- Use local model path if available
- Verify HuggingFace Hub accessibility

#### 3. CUDA/MPS Device Errors

```python
ValueError: CUDA requested but not available
```

**Solutions:**
- Install PyTorch with CUDA support
- Use CPU fallback by setting device manually
- Check GPU drivers and compatibility

#### 4. Memory Issues

```python
RuntimeError: CUDA out of memory
```

**Solutions:**
- Reduce batch size: `LEGAL_BERT_BATCH_SIZE=16`
- Use CPU: Force device selection
- Close other GPU applications

#### 5. Configuration Errors

```python
error: Legal BERT requires 1024 embedding dimensions, got: 1536
```

**Solution:**
```bash
# Remove or correct dimension override
unset EMBEDDING_DIMENSIONS
# or
export EMBEDDING_DIMENSIONS=1024
```

### Debugging

#### Enable Debug Logging

```python
import logging
logging.getLogger("vector_service.embeddings.LegalBERTEmbedder").setLevel(logging.DEBUG)
```

#### Validate Configuration

```python
from vector_service.config import VectorConfig

config = VectorConfig()
validation_result = config.validate()

if not validation_result["success"]:
    print(f"Config error: {validation_result['error']}")
```

#### Test Provider Creation

```python
from vector_service.embeddings import EmbedderFactory
from vector_service.config import VectorConfig

config = VectorConfig()
result = EmbedderFactory.create_embedder(config, "legal_bert")

if not result["success"]:
    print(f"Creation error: {result['error']}")
else:
    print(f"Success: {result['provider']} ({result['dimensions']} dims)")
```

## Migration Guide

### From OpenAI to Legal BERT

1. **Install dependencies**:
   ```bash
   pip install torch>=2.1.0 transformers>=4.41.0
   ```

2. **Update environment variables**:
   ```bash
   export EMBEDDING_PROVIDER=legal_bert
   export LEGAL_BERT_MODEL_PATH=nlpaueb/legal-bert-base-uncased
   ```

3. **No code changes required** - existing VectorService usage works unchanged

4. **Handle dimension differences**:
   - OpenAI: 1536 dimensions (default)
   - Legal BERT: 1024 dimensions (fixed)
   - Qdrant collections are dimension-specific

### Dual Provider Setup

Use different collections for different providers:

```python
# OpenAI collection
os.environ["EMBEDDING_PROVIDER"] = "openai"
os.environ["QDRANT_COLLECTION_NAME"] = "emails_openai"
openai_service = VectorService()

# Legal BERT collection
os.environ["EMBEDDING_PROVIDER"] = "legal_bert"
os.environ["QDRANT_COLLECTION_NAME"] = "emails_legal_bert"
legal_bert_service = VectorService()
```

### Backward Compatibility

All existing code using `EmailEmbedder` continues to work:

```python
# This still works unchanged
from vector_service.embeddings import EmailEmbedder

config = VectorConfig()
embedder = EmailEmbedder(config)  # Creates OpenAIEmbedder
```

## Best Practices

### 1. Model Caching

```python
# Pre-load model in application startup
embedder = EmbedderFactory.create_embedder(config, "legal_bert")
# Model is now cached for subsequent requests
```

### 2. Batch Processing

```python
# Process texts in batches for efficiency
batch_size = 32
for i in range(0, len(texts), batch_size):
    batch = texts[i:i+batch_size]
    result = embedder.generate_batch_embeddings(batch)
```

### 3. Error Handling

```python
# Always check success before using results
result = embedder.generate_embedding(text)
if result["success"]:
    embedding = result["embedding"]
    # Process embedding
else:
    # Log error and handle gracefully
    logger.error(f"Embedding failed: {result['error']}")
```

### 4. Resource Management

```python
# Monitor memory usage for large batches
import psutil
memory_usage = psutil.virtual_memory().percent
if memory_usage > 80:
    # Reduce batch size or switch to CPU
    pass
```

### 5. Configuration Validation

```python
# Validate configuration before processing
config = VectorConfig()
if not config.validate()["success"]:
    # Handle configuration errors
    pass
```

---

**Last Updated**: January 2025
**Version**: 1.0
**Legal BERT Model**: pile-of-law/legalbert-large-1.7M-2

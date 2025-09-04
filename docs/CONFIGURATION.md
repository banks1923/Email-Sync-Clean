# Configuration Guide

This document centralizes information about environment variables, ports, and key file paths for the Litigator Solo project.

## Environment Variables

The following environment variables are used to configure the application. They can be set in a `.env` file in the project root, which is loaded by the `.envrc` file.

| Variable | Description | Default Value |
|---|---|---|
| `PYTHONPATH` | The Python path for the project. | `$PWD` |
| `LOG_LEVEL` | The logging level for the application. | `INFO` |
| `QDRANT__STORAGE__PATH` | The storage path for the Qdrant vector database. | `./qdrant_data` |
| `QDRANT__LOG__PATH` | The log path for the Qdrant vector database. | `./logs/qdrant.log` |
| `MCP_STORAGE_DIR` | The storage directory for the MCP sequential thinking server. | `$PWD/data/sequential_thinking` |
| `ENTITY_SPACY_MODEL` | The spaCy model to use for entity extraction. | `en_core_web_sm` |
| `ENTITY_BATCH_SIZE` | The batch size for entity extraction. | `100` |
| `ENTITY_CONFIDENCE_THRESHOLD` | The confidence threshold for entity extraction. | `0.5` |
| `ENTITY_TYPES` | The entity types to extract. | `PERSON,ORG,GPE,MONEY,DATE` |
| `ENTITY_DB_PATH` | The path to the database for the entity service. | `data/system_data/emails.db` |
| `ENTITY_DB_CONNECTIONS` | The maximum number of database connections for the entity service. | `5` |
| `ENTITY_MAX_TEXT_LENGTH` | The maximum text length for entity extraction. | `10000` |
| `ENTITY_NORMALIZE` | Whether to enable text normalization for entity extraction. | `true` |
| `ANTHROPIC_API_KEY` | The API key for Anthropic models. | `None` |
| `OPENAI_API_KEY` | The API key for OpenAI models. | `None` |
| `PERPLEXITY_API_KEY` | The API key for Perplexity models. | `None` |
| `GOOGLE_API_KEY` | The API key for Google models. | `None` |
| `MISTRAL_API_KEY` | The API key for Mistral models. | `None` |

## Key File Paths

| Path | Description |
|---|---|
| `data/system_data/emails.db` | The main SQLite database for the application. |
| `qdrant_data/` | The storage directory for the Qdrant vector database. |
| `logs/` | The directory for log files. |
| `data/sequential_thinking/` | The storage directory for the MCP sequential thinking server. |
| `.config/` | The directory for tool configurations. |
| `~/Secrets/.env` | The centralized location for secrets and API keys. |

## Service Configuration

### Gmail Service

The Gmail service is configured in `gmail/config.py`. The configuration includes:

*   **Preferred Senders:** A list of email addresses to prioritize during sync.
*   **Excluded Dates:** A list of dates to exclude from sync.

### Entity Service

The Entity service is configured in `entity/config.py`. The configuration includes:

*   **SpaCy Model:** The spaCy model to use for entity extraction.
*   **Batch Size:** The batch size for entity extraction.
*   **Confidence Threshold:** The confidence threshold for entity extraction.
*   **Entity Types:** The entity types to extract.
*   **Database Path:** The path to the database for the entity service.

## MCP Server Configuration

The MCP server configuration is located in `infrastructure/mcp_config/config.py`. This file defines the MCP servers available to the system, including:

*   `legal-intelligence`
*   `search-intelligence`
*   `filesystem`
*   `sequential-thinking`
*   `task-master-ai`

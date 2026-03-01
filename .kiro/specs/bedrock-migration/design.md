# Design Document: AFIRGen Bedrock Migration

## Overview

This design document specifies the technical architecture for migrating the AFIRGen (Automated FIR Generation) system from self-hosted GGUF models on GPU instances to AWS managed services. The migration replaces expensive GPU infrastructure (~$1.21/hour for g5.2xlarge) with pay-per-use AWS services while maintaining all existing functionality, security standards, and role-based access control.

### Current Architecture

The existing system runs on a g5.2xlarge GPU instance with:
- Self-hosted Whisper model for audio transcription
- Self-hosted Donut OCR model for document processing
- Custom legal models for FIR generation
- ChromaDB for vector storage of IPC sections
- FastAPI backend
- MySQL RDS for FIR storage
- S3 for file storage

### Target Architecture

The new architecture uses AWS managed services:
- Amazon Transcribe for audio transcription (supports 10 Indian languages)
- Amazon Textract for document OCR
- Amazon Bedrock with Claude 3 Sonnet for legal text processing
- Amazon Bedrock with Titan Embeddings for vector generation
- OpenSearch Serverless or Aurora PostgreSQL with pgvector for vector storage
- FastAPI backend on t3.small/medium instances
- Existing MySQL RDS and S3 infrastructure

### Migration Goals

1. **Cost Reduction**: Eliminate GPU instance costs by moving to pay-per-use services
2. **Operational Simplicity**: Remove model hosting and maintenance burden
3. **Scalability**: Leverage AWS managed service auto-scaling
4. **Backward Compatibility**: Maintain existing API contracts and frontend compatibility
5. **Security**: Maintain encryption, IAM-based access, and RBAC
6. **Performance**: Match or exceed current processing times
7. **Rollback Safety**: Support feature flag to revert to GGUF if needed

## Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        FE[Frontend Application]
    end
    
    subgraph "Application Layer - EC2 t3.small/medium"
        API[FastAPI Backend]
        Cache[IPC Section Cache]
    end
    
    subgraph "AWS Managed Services"
        Transcribe[Amazon Transcribe<br/>10 Indian Languages]
        Textract[Amazon Textract<br/>Document OCR]
        Bedrock[Amazon Bedrock<br/>Claude 3 Sonnet]
        Titan[Amazon Bedrock<br/>Titan Embeddings]
    end
    
    subgraph "Storage Layer"
        S3[S3 Buckets<br/>SSE-KMS Encrypted]
        RDS[(MySQL RDS<br/>FIR Storage)]
        Vector[(Vector Database<br/>OpenSearch or Aurora pgvector)]
    end
    
    subgraph "Observability"
        CW[CloudWatch<br/>Metrics & Logs]
        XRay[X-Ray<br/>Distributed Tracing]
    end
    
    FE -->|HTTPS| API
    API -->|Audio Files| S3
    API -->|Image Files| S3
    S3 -->|S3 URI| Transcribe
    S3 -->|S3 URI| Textract
    API -->|Legal Text| Bedrock
    API -->|Text for Embedding| Titan
    API -->|Vector Search| Vector
    API -->|Store FIR| RDS
    API -->|Metrics & Logs| CW
    API -->|Traces| XRay
    Titan -->|Store Embeddings| Vector
```

### Component Architecture

#### 1. Audio Processing Pipeline

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant S3
    participant Transcribe
    participant CW as CloudWatch
    
    Client->>API: Upload audio file
    API->>API: Validate format (WAV/MP3/MPEG)
    API->>S3: Upload with SSE-KMS
    API->>Transcribe: Start transcription job
    Transcribe->>S3: Read audio file
    Transcribe->>Transcribe: Process audio
    API->>Transcribe: Poll for completion
    Transcribe->>API: Return transcript
    API->>S3: Delete temp file
    API->>CW: Log metrics
    API->>Client: Return transcript
```

#### 2. Document Processing Pipeline

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant S3
    participant Textract
    participant CW as CloudWatch
    
    Client->>API: Upload image file
    API->>API: Validate format (JPEG/PNG)
    API->>S3: Upload with SSE-KMS
    API->>Textract: Detect document text
    Textract->>S3: Read image file
    Textract->>Textract: Extract text
    Textract->>API: Return extracted text
    API->>S3: Delete temp file
    API->>CW: Log metrics
    API->>Client: Return text
```

#### 3. FIR Generation Pipeline with RAG

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Bedrock
    participant Titan
    participant Vector
    participant RDS
    
    Client->>API: Submit complaint text
    API->>Bedrock: Generate formal narrative
    Bedrock->>API: Return narrative
    API->>Bedrock: Extract metadata
    Bedrock->>API: Return structured data
    API->>Titan: Generate query embedding
    Titan->>API: Return embedding vector
    API->>Vector: Similarity search
    Vector->>API: Return top 5 IPC sections
    API->>Bedrock: Generate FIR with RAG
    Bedrock->>API: Return complete FIR
    API->>RDS: Store FIR
    API->>Client: Return FIR
```

### Network Architecture

The system maintains the existing VPC architecture with security enhancements:

- **Public Subnets**: EC2 instances with Elastic IP for API access
- **Private Subnets**: RDS MySQL and vector database (no internet access)
- **VPC Endpoints**: For Bedrock, Transcribe, Textract, S3 (cost optimization and security)
- **Security Groups**: Restrictive ingress/egress rules
- **IAM Roles**: Service-specific permissions with least privilege

### Deployment Architecture

```mermaid
graph TB
    subgraph "VPC"
        subgraph "Public Subnet"
            EC2[EC2 t3.small/medium<br/>FastAPI Backend]
            NAT[NAT Gateway]
        end
        
        subgraph "Private Subnet 1"
            RDS[(MySQL RDS)]
        end
        
        subgraph "Private Subnet 2"
            Vector[(Vector DB)]
        end
        
        subgraph "VPC Endpoints"
            VPE_Bedrock[Bedrock Endpoint]
            VPE_S3[S3 Endpoint]
            VPE_Transcribe[Transcribe Endpoint]
            VPE_Textract[Textract Endpoint]
        end
    end
    
    Internet[Internet] -->|HTTPS| EC2
    EC2 -->|Private| RDS
    EC2 -->|Private| Vector
    EC2 -->|VPC Endpoint| VPE_Bedrock
    EC2 -->|VPC Endpoint| VPE_S3
    EC2 -->|VPC Endpoint| VPE_Transcribe
    EC2 -->|VPC Endpoint| VPE_Textract
```

## Components and Interfaces

### 1. AWS Service Integration Layer

#### TranscribeClient

Handles audio transcription using Amazon Transcribe.

```python
class TranscribeClient:
    """
    Manages audio transcription using Amazon Transcribe.
    Supports 10 Indian languages with automatic language detection.
    """
    
    def __init__(self, region: str, s3_bucket: str):
        self.client = boto3.client('transcribe', region_name=region)
        self.s3_bucket = s3_bucket
        self.max_retries = 2
        self.supported_languages = [
            'hi-IN', 'en-IN', 'ta-IN', 'te-IN', 'bn-IN',
            'mr-IN', 'gu-IN', 'kn-IN', 'ml-IN', 'pa-IN'
        ]
    
    async def transcribe_audio(
        self,
        audio_file: UploadFile,
        language_code: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio file to text.
        
        Args:
            audio_file: Audio file (WAV, MP3, MPEG)
            language_code: Optional language code (auto-detect if None)
        
        Returns:
            TranscriptionResult with transcript text and metadata
        
        Raises:
            ValidationError: Invalid file format
            TranscribeError: Transcription failed after retries
        """
        pass
    
    async def _upload_to_s3(self, file: UploadFile) -> str:
        """Upload file to S3 with SSE-KMS encryption."""
        pass
    
    async def _start_transcription_job(
        self,
        s3_uri: str,
        language_code: str
    ) -> str:
        """Start Transcribe job and return job name."""
        pass
    
    async def _poll_transcription_job(self, job_name: str) -> dict:
        """Poll job status until completion with exponential backoff."""
        pass
    
    async def _cleanup_s3_file(self, s3_uri: str):
        """Delete temporary file from S3."""
        pass
```

#### TextractClient

Handles document OCR using Amazon Textract.

```python
class TextractClient:
    """
    Manages document text extraction using Amazon Textract.
    Supports both plain text and structured form data extraction.
    """
    
    def __init__(self, region: str, s3_bucket: str):
        self.client = boto3.client('textract', region_name=region)
        self.s3_bucket = s3_bucket
        self.max_retries = 2
    
    async def extract_text(
        self,
        image_file: UploadFile,
        extract_forms: bool = True
    ) -> ExtractionResult:
        """
        Extract text from document image.
        
        Args:
            image_file: Image file (JPEG, PNG)
            extract_forms: Whether to extract structured form data
        
        Returns:
            ExtractionResult with extracted text and form data
        
        Raises:
            ValidationError: Invalid file format
            TextractError: Extraction failed after retries
        """
        pass
    
    async def _upload_to_s3(self, file: UploadFile) -> str:
        """Upload file to S3 with SSE-KMS encryption."""
        pass
    
    async def _detect_document_text(self, s3_uri: str) -> dict:
        """Call Textract DetectDocumentText API."""
        pass
    
    async def _analyze_document(self, s3_uri: str) -> dict:
        """Call Textract AnalyzeDocument API for forms."""
        pass
    
    async def _cleanup_s3_file(self, s3_uri: str):
        """Delete temporary file from S3."""
        pass
```

#### BedrockClient

Handles legal text processing using Claude 3 Sonnet via Amazon Bedrock.

```python
class BedrockClient:
    """
    Manages legal text processing using Claude 3 Sonnet via Bedrock.
    Implements rate limiting, retry logic, and token usage tracking.
    """
    
    def __init__(
        self,
        region: str,
        model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    ):
        self.client = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id
        self.max_retries = 2
        self.semaphore = asyncio.Semaphore(10)  # Max 10 concurrent calls
    
    async def generate_formal_narrative(
        self,
        complaint_text: str
    ) -> FormalNarrative:
        """
        Convert raw complaint text to formal legal narrative.
        
        Args:
            complaint_text: Raw complaint text from user
        
        Returns:
            FormalNarrative with formatted legal text (max 3 sentences)
        
        Raises:
            BedrockError: Generation failed after retries
        """
        pass
    
    async def extract_metadata(
        self,
        narrative: str
    ) -> ComplaintMetadata:
        """
        Extract structured metadata from formal narrative.
        
        Args:
            narrative: Formal legal narrative
        
        Returns:
            ComplaintMetadata with incident type, date, location, parties
        
        Raises:
            BedrockError: Extraction failed after retries
            ValidationError: Missing required fields
        """
        pass
    
    async def generate_fir(
        self,
        narrative: str,
        metadata: ComplaintMetadata,
        ipc_sections: List[IPCSection]
    ) -> FIR:
        """
        Generate complete FIR using RAG with IPC sections.
        
        Args:
            narrative: Formal legal narrative
            metadata: Extracted complaint metadata
            ipc_sections: Relevant IPC sections from vector search
        
        Returns:
            Complete FIR in standard format
        
        Raises:
            BedrockError: Generation failed after retries
            ValidationError: Missing required FIR fields
        """
        pass
    
    async def _invoke_model(
        self,
        prompt: str,
        max_tokens: int = 1024
    ) -> dict:
        """
        Invoke Claude model with retry and rate limiting.
        Implements exponential backoff with jitter for throttling.
        """
        pass
```

#### TitanEmbeddingsClient

Handles vector embedding generation using Titan Embeddings.

```python
class TitanEmbeddingsClient:
    """
    Manages vector embedding generation using Titan Embeddings.
    Generates 1536-dimensional embeddings for text.
    """
    
    def __init__(
        self,
        region: str,
        model_id: str = "amazon.titan-embed-text-v1"
    ):
        self.client = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id
        self.embedding_dimension = 1536
        self.max_retries = 2
    
    async def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding vector for text.
        
        Args:
            text: Input text to embed
        
        Returns:
            1536-dimensional numpy array
        
        Raises:
            BedrockError: Embedding generation failed after retries
        """
        pass
    
    async def generate_batch_embeddings(
        self,
        texts: List[str],
        batch_size: int = 25
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of input texts
            batch_size: Number of texts per batch
        
        Returns:
            List of embedding vectors
        """
        pass
```

### 2. Vector Database Layer

#### VectorDatabaseInterface

Abstract interface for vector database operations.

```python
class VectorDatabaseInterface(ABC):
    """
    Abstract interface for vector database operations.
    Supports both OpenSearch Serverless and Aurora pgvector.
    """
    
    @abstractmethod
    async def connect(self):
        """Establish connection to vector database."""
        pass
    
    @abstractmethod
    async def create_index(self, index_name: str, dimension: int):
        """Create vector index if not exists."""
        pass
    
    @abstractmethod
    async def insert_vectors(
        self,
        vectors: List[np.ndarray],
        metadata: List[dict]
    ):
        """Insert vectors with associated metadata."""
        pass
    
    @abstractmethod
    async def similarity_search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5
    ) -> List[SearchResult]:
        """Perform cosine similarity search."""
        pass
    
    @abstractmethod
    async def delete_vectors(self, ids: List[str]):
        """Delete vectors by ID."""
        pass
    
    @abstractmethod
    async def close(self):
        """Close database connection."""
        pass
```

#### OpenSearchVectorDB

Implementation for OpenSearch Serverless.

```python
class OpenSearchVectorDB(VectorDatabaseInterface):
    """
    Vector database implementation using OpenSearch Serverless.
    Uses k-NN plugin for vector similarity search.
    """
    
    def __init__(
        self,
        endpoint: str,
        region: str,
        index_name: str = "ipc_sections"
    ):
        self.endpoint = endpoint
        self.region = region
        self.index_name = index_name
        self.client = None
        self.max_retries = 2
    
    async def connect(self):
        """Connect using AWS SigV4 authentication."""
        pass
    
    async def create_index(self, index_name: str, dimension: int):
        """
        Create k-NN index with cosine similarity.
        
        Index mapping:
        {
            "settings": {
                "index.knn": true
            },
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 1536,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    },
                    "ipc_section": {"type": "keyword"},
                    "description": {"type": "text"},
                    "penalty": {"type": "text"}
                }
            }
        }
        """
        pass
    
    async def similarity_search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Perform k-NN search with cosine similarity.
        
        Query:
        {
            "size": top_k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_vector.tolist(),
                        "k": top_k
                    }
                }
            }
        }
        """
        pass
```

#### AuroraPgVectorDB

Implementation for Aurora PostgreSQL with pgvector.

```python
class AuroraPgVectorDB(VectorDatabaseInterface):
    """
    Vector database implementation using Aurora PostgreSQL with pgvector.
    Uses pgvector extension for vector similarity search.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        table_name: str = "ipc_sections"
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.table_name = table_name
        self.pool = None
        self.max_retries = 2
    
    async def connect(self):
        """Create asyncpg connection pool with SSL."""
        pass
    
    async def create_index(self, index_name: str, dimension: int):
        """
        Create table with vector column and IVFFlat index.
        
        SQL:
        CREATE EXTENSION IF NOT EXISTS vector;
        
        CREATE TABLE IF NOT EXISTS ipc_sections (
            id SERIAL PRIMARY KEY,
            ipc_section VARCHAR(50) NOT NULL,
            description TEXT NOT NULL,
            penalty TEXT,
            embedding vector(1536) NOT NULL
        );
        
        CREATE INDEX ON ipc_sections 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        """
        pass
    
    async def similarity_search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Perform cosine similarity search using pgvector.
        
        SQL:
        SELECT ipc_section, description, penalty,
               1 - (embedding <=> $1) AS similarity
        FROM ipc_sections
        ORDER BY embedding <=> $1
        LIMIT $2;
        """
        pass
```

### 3. Service Layer

#### FIRGenerationService

Orchestrates the complete FIR generation workflow.

```python
class FIRGenerationService:
    """
    Orchestrates FIR generation workflow with RAG.
    Coordinates Bedrock, vector database, and storage operations.
    """
    
    def __init__(
        self,
        bedrock_client: BedrockClient,
        embeddings_client: TitanEmbeddingsClient,
        vector_db: VectorDatabaseInterface,
        ipc_cache: IPCCache
    ):
        self.bedrock = bedrock_client
        self.embeddings = embeddings_client
        self.vector_db = vector_db
        self.cache = ipc_cache
    
    async def generate_fir_from_text(
        self,
        complaint_text: str,
        user_id: str,
        role: str
    ) -> FIR:
        """
        Generate FIR from raw complaint text.
        
        Workflow:
        1. Generate formal narrative using Claude
        2. Extract metadata using Claude
        3. Generate query embedding using Titan
        4. Search for relevant IPC sections
        5. Generate complete FIR using Claude with RAG
        6. Store FIR in MySQL with RBAC
        
        Args:
            complaint_text: Raw complaint text
            user_id: User ID for RBAC
            role: User role for RBAC
        
        Returns:
            Complete FIR object
        
        Raises:
            ValidationError: Invalid input or missing required fields
            ServiceError: Generation failed after retries
        """
        pass
    
    async def generate_fir_from_audio(
        self,
        audio_file: UploadFile,
        language_code: Optional[str],
        user_id: str,
        role: str
    ) -> FIR:
        """Generate FIR from audio file (transcribe then process)."""
        pass
    
    async def generate_fir_from_image(
        self,
        image_file: UploadFile,
        user_id: str,
        role: str
    ) -> FIR:
        """Generate FIR from document image (OCR then process)."""
        pass
    
    async def _retrieve_relevant_ipc_sections(
        self,
        narrative: str
    ) -> List[IPCSection]:
        """
        Retrieve relevant IPC sections using RAG.
        Checks cache first, then performs vector search.
        """
        pass
```

### 4. Caching Layer

#### IPCCache

In-memory cache for frequently accessed IPC sections.

```python
class IPCCache:
    """
    In-memory LRU cache for IPC sections.
    Reduces embedding API calls for frequently accessed sections.
    """
    
    def __init__(self, max_size: int = 100):
        self.cache = {}  # query_hash -> List[IPCSection]
        self.max_size = max_size
        self.access_order = []  # LRU tracking
    
    def get(self, query_text: str) -> Optional[List[IPCSection]]:
        """Get cached IPC sections for query."""
        pass
    
    def put(self, query_text: str, sections: List[IPCSection]):
        """Cache IPC sections for query with LRU eviction."""
        pass
    
    def _compute_hash(self, text: str) -> str:
        """Compute hash for cache key."""
        pass
```

### 5. Retry and Circuit Breaker

#### RetryHandler

Implements exponential backoff with jitter for AWS service retries.

```python
class RetryHandler:
    """
    Implements retry logic with exponential backoff and jitter.
    Handles throttling, transient errors, and rate limits.
    """
    
    def __init__(
        self,
        max_retries: int = 2,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic.
        
        Retry conditions:
        - Throttling errors (429, ThrottlingException)
        - Server errors (5xx)
        - Transient network errors
        
        Backoff formula:
        delay = min(base_delay * (2 ** attempt) + random_jitter, max_delay)
        """
        pass
```

#### CircuitBreaker

Implements circuit breaker pattern for AWS services.

```python
class CircuitBreaker:
    """
    Circuit breaker for AWS service calls.
    Prevents cascading failures by failing fast when service is down.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.state = "closed"  # closed, open, half_open
        self.failure_count = 0
        self.last_failure_time = None
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        States:
        - Closed: Normal operation, track failures
        - Open: Fail fast, return error immediately
        - Half-Open: Allow limited test requests
        """
        pass
```

### 6. Monitoring and Observability

#### MetricsCollector

Collects and emits CloudWatch metrics.

```python
class MetricsCollector:
    """
    Collects and emits CloudWatch metrics for AWS service operations.
    Tracks latency, success rate, token usage, and costs.
    """
    
    def __init__(self, namespace: str = "AFIRGen/Bedrock"):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = namespace
    
    def record_transcribe_request(
        self,
        duration: float,
        success: bool,
        language: str
    ):
        """Record Transcribe API metrics."""
        pass
    
    def record_textract_request(
        self,
        duration: float,
        success: bool
    ):
        """Record Textract API metrics."""
        pass
    
    def record_bedrock_request(
        self,
        duration: float,
        success: bool,
        input_tokens: int,
        output_tokens: int,
        model_id: str
    ):
        """Record Bedrock API metrics including token usage."""
        pass
    
    def record_vector_search(
        self,
        duration: float,
        success: bool,
        result_count: int
    ):
        """Record vector database operation metrics."""
        pass
    
    def record_fir_generation(
        self,
        duration: float,
        success: bool,
        source: str  # text, audio, image
    ):
        """Record end-to-end FIR generation metrics."""
        pass
```

## Database Schemas

### MySQL RDS Schema

The system uses MySQL RDS for storing FIR records and background tasks. The schema maintains backward compatibility with the existing GGUF implementation.

#### 1. fir_records Table

Stores all First Information Reports with metadata and status tracking.

```sql
CREATE TABLE IF NOT EXISTS fir_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fir_number VARCHAR(100) UNIQUE NOT NULL,
    session_id VARCHAR(100),
    user_id VARCHAR(100),
    complaint_text TEXT,
    fir_content TEXT,
    violations_json LONGTEXT,
    status ENUM('pending', 'finalized') DEFAULT 'pending',
    finalized_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for query optimization
    INDEX idx_fir_number (fir_number),
    INDEX idx_session_id (session_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Field Descriptions:**
- `id`: Auto-incrementing primary key
- `fir_number`: Unique FIR identifier (format: FIR-YYYYMMDD-XXXXX)
- `session_id`: Session identifier for tracking user sessions
- `user_id`: User identifier for RBAC
- `complaint_text`: Original complaint text (raw input)
- `fir_content`: Generated FIR in structured format
- `violations_json`: JSON array of IPC sections (e.g., `["IPC 420", "IPC 406"]`)
- `status`: FIR status (pending or finalized)
- `finalized_at`: Timestamp when FIR was finalized
- `created_at`: Timestamp when FIR was created

**RBAC Enforcement:**
- Admin: Full CRUD access
- Officer: SELECT, INSERT, UPDATE
- Viewer: SELECT only
- Clerk: INSERT only

#### 2. background_tasks Table

Tracks asynchronous background tasks for long-running operations.

```sql
CREATE TABLE IF NOT EXISTS background_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE NOT NULL,
    task_name VARCHAR(255) NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    priority INT DEFAULT 5,
    status ENUM('pending', 'running', 'completed', 'failed', 'cancelled') DEFAULT 'pending',
    params JSON,
    result JSON,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    
    -- Indexes for query optimization
    INDEX idx_task_id (task_id),
    INDEX idx_task_name (task_name),
    INDEX idx_task_type (task_type),
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_created_at (created_at),
    INDEX idx_status_priority (status, priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Field Descriptions:**
- `id`: Auto-incrementing primary key
- `task_id`: Unique task identifier (UUID)
- `task_name`: Human-readable task name
- `task_type`: Task category (e.g., "transcription", "ocr", "fir_generation")
- `priority`: Task priority (1-10, lower is higher priority)
- `status`: Task execution status
- `params`: JSON object with task parameters
- `result`: JSON object with task results
- `error_message`: Error details if task failed
- `retry_count`: Number of retry attempts
- `max_retries`: Maximum allowed retries
- `created_at`: Task creation timestamp
- `started_at`: Task execution start timestamp
- `completed_at`: Task completion timestamp

### Vector Database Schema

The system supports two vector database implementations with identical logical schemas.

#### OpenSearch Serverless Schema

Index mapping for k-NN vector search with cosine similarity.

```json
{
  "settings": {
    "index.knn": true,
    "index.knn.algo_param.ef_search": 100
  },
  "mappings": {
    "properties": {
      "ipc_section": {
        "type": "keyword"
      },
      "description": {
        "type": "text",
        "analyzer": "standard"
      },
      "penalty": {
        "type": "text"
      },
      "embedding": {
        "type": "knn_vector",
        "dimension": 1536,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimil",
          "engine": "nmslib",
          "parameters": {
            "ef_construction": 128,
            "m": 16
          }
        }
      },
      "created_at": {
        "type": "date"
      }
    }
  }
}
```

**Field Descriptions:**
- `ipc_section`: IPC section number (e.g., "IPC 420", "IPC 406")
- `description`: Full text description of the IPC section
- `penalty`: Penalty/punishment details for the offense
- `embedding`: 1536-dimensional vector from Titan Embeddings
- `created_at`: Timestamp when embedding was created

**Index Configuration:**
- Algorithm: HNSW (Hierarchical Navigable Small World)
- Distance metric: Cosine similarity
- ef_construction: 128 (index build quality)
- m: 16 (number of connections per node)

#### Aurora PostgreSQL with pgvector Schema

Table schema for vector storage using pgvector extension.

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create IPC sections table with vector column
CREATE TABLE IF NOT EXISTS ipc_sections (
    id SERIAL PRIMARY KEY,
    ipc_section VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    penalty TEXT,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for query optimization
    INDEX idx_ipc_section (ipc_section)
);

-- Create IVFFlat index for fast similarity search
CREATE INDEX ON ipc_sections 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create GIN index for full-text search on description
CREATE INDEX idx_description_gin ON ipc_sections 
USING gin(to_tsvector('english', description));
```

**Field Descriptions:**
- `id`: Auto-incrementing primary key
- `ipc_section`: IPC section number (e.g., "IPC 420", "IPC 406")
- `description`: Full text description of the IPC section
- `penalty`: Penalty/punishment details for the offense
- `embedding`: 1536-dimensional vector from Titan Embeddings (pgvector type)
- `created_at`: Timestamp when embedding was created

**Index Configuration:**
- IVFFlat index with 100 lists for approximate nearest neighbor search
- Distance operator: `<=>` (cosine distance)
- GIN index for full-text search on description field

**Similarity Search Query:**
```sql
SELECT 
    ipc_section, 
    description, 
    penalty,
    1 - (embedding <=> $1::vector) AS similarity
FROM ipc_sections
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

### Schema Migration Strategy

#### From ChromaDB to New Vector Database

1. **Export Phase:**
   - Extract all IPC sections from ChromaDB
   - Export format: JSON with schema `[{section, description, penalty, embedding}]`
   - Validate export completeness (count check)

2. **Transform Phase:**
   - Generate new embeddings using Titan Embeddings (1536 dimensions)
   - Validate embedding dimensionality
   - Preserve all metadata (section, description, penalty)

3. **Load Phase:**
   - Batch insert into target vector database (25 records per batch)
   - Create indexes after bulk load for performance
   - Verify record count matches source

4. **Validation Phase:**
   - Perform sample similarity searches
   - Compare results with ChromaDB baseline
   - Validate cosine similarity scores

#### MySQL Schema Compatibility

No schema changes required for MySQL RDS. The existing `fir_records` and `background_tasks` tables remain unchanged, ensuring zero downtime migration.

## Data Models

### Request/Response Models

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TranscriptionResult(BaseModel):
    """Result from audio transcription."""
    transcript: str
    language_code: str
    confidence: float
    duration_seconds: float

class ExtractionResult(BaseModel):
    """Result from document OCR."""
    text: str
    form_data: Optional[dict] = None
    confidence: float

class FormalNarrative(BaseModel):
    """Formal legal narrative generated by Claude."""
    narrative: str = Field(..., max_length=500)
    sentence_count: int = Field(..., le=3)

class ComplaintMetadata(BaseModel):
    """Structured metadata extracted from complaint."""
    incident_type: str
    incident_date: datetime
    incident_location: str
    accused_details: Optional[str] = None
    victim_details: Optional[str] = None

class IPCSection(BaseModel):
    """IPC section with metadata."""
    section_number: str
    description: str
    penalty: str
    similarity_score: float

class FIR(BaseModel):
    """Complete First Information Report."""
    fir_number: str
    complainant_name: str
    complainant_address: str
    complainant_phone: str
    incident_type: str
    incident_date: datetime
    incident_location: str
    incident_description: str
    accused_details: Optional[str] = None
    victim_details: Optional[str] = None
    ipc_sections: List[str]
    investigating_officer: str
    station_name: str
    created_at: datetime
    created_by: str

class SearchResult(BaseModel):
    """Vector search result."""
    ipc_section: IPCSection
    score: float
```

### Configuration Models

```python
class AWSConfig(BaseModel):
    """AWS service configuration."""
    region: str = Field(default="ap-south-1")
    s3_bucket: str
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-sonnet-20240229-v1:0"
    )
    embeddings_model_id: str = Field(
        default="amazon.titan-embed-text-v1"
    )
    transcribe_languages: List[str] = Field(
        default=[
            "hi-IN", "en-IN", "ta-IN", "te-IN", "bn-IN",
            "mr-IN", "gu-IN", "kn-IN", "ml-IN", "pa-IN"
        ]
    )

class VectorDBConfig(BaseModel):
    """Vector database configuration."""
    db_type: str = Field(..., regex="^(opensearch|aurora_pgvector)$")
    endpoint: str
    index_name: str = Field(default="ipc_sections")
    dimension: int = Field(default=1536)
    
    # OpenSearch specific
    opensearch_region: Optional[str] = None
    
    # Aurora pgvector specific
    pg_host: Optional[str] = None
    pg_port: Optional[int] = None
    pg_database: Optional[str] = None
    pg_user: Optional[str] = None
    pg_password: Optional[str] = None

class FeatureFlags(BaseModel):
    """Feature flags for gradual rollout."""
    enable_bedrock: bool = Field(default=True)
    enable_caching: bool = Field(default=True)
    enable_xray: bool = Field(default=True)
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

After analyzing the acceptance criteria, I've identified properties that eliminate redundancy. Many criteria share common patterns (retry logic, cleanup, metrics) that can be consolidated into comprehensive properties.

### Property 1: File Format Validation

*For any* uploaded file (audio or image), the system should accept only files with valid formats (WAV/MP3/MPEG for audio, JPEG/PNG for images) and reject all other formats with appropriate error messages.

**Validates: Requirements 1.1, 2.1**

### Property 2: S3 Encryption

*For any* file uploaded to S3 (audio, image, or temporary files), the S3 object metadata should indicate SSE-KMS encryption is enabled.

**Validates: Requirements 1.2, 2.2, 13.1**

### Property 3: Supported Language Codes

*For any* language code from the set {hi-IN, en-IN, ta-IN, te-IN, bn-IN, mr-IN, gu-IN, kn-IN, ml-IN, pa-IN}, the Transcribe client should accept it as valid, and for any language code outside this set, it should be rejected.

**Validates: Requirements 1.4, 15.1-15.9**

### Property 4: Retry Logic with Exponential Backoff

*For any* AWS service call (Transcribe, Textract, Bedrock, vector database) that fails with a retryable error (throttling, 5xx), the system should retry up to 2 times with exponentially increasing delays and jitter.

**Validates: Requirements 1.6, 2.6, 3.7, 3.8, 4.9, 9.1, 9.2, 9.3, 9.4, 9.5**

### Property 5: Temporary File Cleanup

*For any* temporary file uploaded to S3 during processing (audio or image), after successful processing completion, the file should no longer exist in S3.

**Validates: Requirements 1.8, 2.8, 7.2**

### Property 6: CloudWatch Metrics Emission

*For any* AWS service operation (Transcribe, Textract, Bedrock, vector database, S3), the system should emit CloudWatch metrics including operation count, latency, and success/failure status.

**Validates: Requirements 1.9, 2.9, 3.9, 4.10, 5.9, 7.8, 12.1, 12.2, 12.3, 12.4, 12.5**

### Property 7: Narrative Sentence Limit

*For any* formal legal narrative generated by Claude, the narrative should contain at most 3 sentences.

**Validates: Requirements 3.3**

### Property 8: Metadata Field Completeness

*For any* complaint metadata extracted by Claude, the result should contain all required fields: incident_type, incident_date, incident_location, and optionally accused_details and victim_details.

**Validates: Requirements 3.5, 3.6**

### Property 9: Concurrent Request Limiting

*For any* time window, the number of concurrent Bedrock API calls should never exceed 10.

**Validates: Requirements 3.10**

### Property 10: Embedding Dimensionality

*For any* text embedded using Titan Embeddings, the resulting vector should have exactly 1536 dimensions.

**Validates: Requirements 4.4**

### Property 11: Vector Storage with Metadata

*For any* IPC section embedding stored in the vector database, retrieving it should return both the embedding vector and the associated metadata (section number, description, penalty).

**Validates: Requirements 4.5**

### Property 12: Top-K Search Results

*For any* vector similarity search with k=5, the system should return at most 5 results, ordered by descending similarity score.

**Validates: Requirements 4.8**

### Property 13: FIR Field Completeness

*For any* generated FIR, it should contain all required fields: complainant details, incident details, legal provisions (IPC sections), and investigation details.

**Validates: Requirements 5.4, 5.5**

### Property 14: Role-Based Access Control

*For any* user attempting to store FIR data, the operation should succeed only if the user has the appropriate role permissions.

**Validates: Requirements 5.7, 13.9**

### Property 15: Timeout Configuration

*For any* AWS service client (Transcribe, Textract, Bedrock, S3), the client should be configured with appropriate timeout values to prevent indefinite blocking.

**Validates: Requirements 6.7**

### Property 16: Request Batching

*For any* set of embedding generation requests for multiple texts, if the texts can be batched, the system should make fewer API calls than the number of texts.

**Validates: Requirements 7.3**

### Property 17: Cache Hit Reduction

*For any* IPC section query that results in a cache hit, the system should not make an embedding API call for that query.

**Validates: Requirements 7.7**

### Property 18: API Endpoint Compatibility

*For any* API endpoint that existed in the GGUF implementation, the same endpoint path and HTTP method should exist in the Bedrock implementation.

**Validates: Requirements 8.1**

### Property 19: Schema Compatibility

*For any* API request or response schema from the GGUF implementation, the Bedrock implementation should accept/return the same schema structure.

**Validates: Requirements 8.2, 8.3**

### Property 20: Metrics Structure Compatibility

*For any* CloudWatch metric emitted by the GGUF implementation, the Bedrock implementation should emit a metric with the same name and dimensions.

**Validates: Requirements 8.8**

### Property 21: Circuit Breaker Failure Threshold

*For any* AWS service with a circuit breaker, after 5 consecutive failures, the circuit breaker should open and subsequent requests should fail fast without calling the service.

**Validates: Requirements 9.6, 9.7**

### Property 22: Circuit Breaker Half-Open State

*For any* circuit breaker in half-open state, exactly 3 test requests should be allowed through before deciding whether to close or reopen the circuit.

**Validates: Requirements 9.8**

### Property 23: Error Correlation IDs

*For any* AWS service error logged by the system, the log entry should contain a correlation ID that can be used to trace the request.

**Validates: Requirements 9.9, 12.9**

### Property 24: Configuration Validation

*For any* required environment variable (AWS_REGION, S3_BUCKET_NAME, VECTOR_DB_TYPE), if it is missing at startup, the system should log an error and exit with a non-zero status code.

**Validates: Requirements 11.7, 11.8**

### Property 25: Vector Database Type Validation

*For any* value of VECTOR_DB_TYPE environment variable, the system should accept only "opensearch" or "aurora_pgvector" and reject all other values.

**Validates: Requirements 11.4**

### Property 26: X-Ray Trace Completeness

*For any* FIR generation request, an X-Ray trace should be created that includes subsegments for all AWS service calls made during the request.

**Validates: Requirements 12.6, 12.7**

### Property 27: Structured Logging Format

*For any* log entry for AWS service requests or responses, the log should be in valid JSON format with required fields (timestamp, service, operation, status).

**Validates: Requirements 12.8**

### Property 28: PII Exclusion from Logs

*For any* log entry, it should not contain sensitive data such as complainant names, phone numbers, addresses, or incident descriptions.

**Validates: Requirements 13.4**

### Property 29: Migration Embedding Count Preservation

*For any* migration from ChromaDB to the new vector database, the count of embeddings in the target database should equal the count in the source database after migration completes.

**Validates: Requirements 14.4**

### Property 30: Feature Flag API Contract Consistency

*For any* API endpoint, the request and response schemas should be identical whether ENABLE_BEDROCK is true or false.

**Validates: Requirements 16.7**


## Prompt Engineering

### Claude Prompt Templates

The system uses carefully crafted prompts for each Claude interaction to ensure consistent, high-quality outputs.

#### 1. Legal Narrative Generation Prompt

Converts raw complaint text into formal legal narrative (max 3 sentences).

```python
LEGAL_NARRATIVE_PROMPT = """You are a legal expert assistant helping to convert informal complaint text into formal legal narratives for First Information Reports (FIRs) in India.

Task: Convert the following complaint into a formal legal narrative with exactly 3 sentences or fewer. The narrative should:
- Use formal legal language
- Be factual and objective
- Remove conversational tone
- Maintain all key details (who, what, when, where)
- Be concise and clear

Complaint:
{complaint_text}

Formal Legal Narrative (max 3 sentences):"""
```

**Parameters:**
- Temperature: 0.3 (deterministic, minimal creativity)
- Max tokens: 500
- Stop sequences: None

#### 2. Metadata Extraction Prompt

Extracts structured metadata from formal narrative.

```python
METADATA_EXTRACTION_PROMPT = """You are a legal expert assistant extracting structured information from FIR narratives.

Task: Extract the following information from the legal narrative and return it in JSON format:
- incident_type: Type of crime/incident (e.g., "theft", "assault", "fraud")
- incident_date: Date of incident in ISO 8601 format (YYYY-MM-DD)
- incident_location: Location where incident occurred
- accused_details: Details about the accused person(s) (if mentioned, otherwise null)
- victim_details: Details about the victim(s) (if mentioned, otherwise null)

Legal Narrative:
{narrative}

Return ONLY valid JSON with the above fields. Do not include any explanation or additional text.

JSON:"""
```

**Parameters:**
- Temperature: 0.1 (highly deterministic)
- Max tokens: 300
- Stop sequences: None

**Example Output:**
```json
{
  "incident_type": "theft",
  "incident_date": "2024-01-15",
  "incident_location": "123 Main Street, Mumbai",
  "accused_details": "Unknown male, approximately 30 years old, wearing black jacket",
  "victim_details": "Rajesh Kumar, mobile phone stolen"
}
```

#### 3. FIR Generation with RAG Prompt

Generates complete FIR using formal narrative and retrieved IPC sections.

```python
FIR_GENERATION_PROMPT = """You are a legal expert assistant generating First Information Reports (FIRs) for Indian police stations.

Task: Generate a complete FIR based on the following information:

Formal Legal Narrative:
{narrative}

Incident Metadata:
- Type: {incident_type}
- Date: {incident_date}
- Location: {incident_location}
- Accused: {accused_details}
- Victim: {victim_details}

Relevant IPC Sections (from legal database):
{ipc_sections}

Generate a complete FIR in the following format:

FIR Number: [Auto-generated]
Date of Report: [Current date]
Police Station: {station_name}

COMPLAINANT DETAILS:
Name: {complainant_name}
Address: {complainant_address}
Phone: {complainant_phone}

INCIDENT DETAILS:
Type of Incident: {incident_type}
Date and Time: {incident_date}
Location: {incident_location}

DESCRIPTION OF INCIDENT:
[Detailed description based on the formal narrative]

ACCUSED DETAILS:
[Details if available, otherwise "Unknown"]

VICTIM DETAILS:
[Details if available]

LEGAL PROVISIONS:
[List all applicable IPC sections with brief descriptions]

INVESTIGATION DETAILS:
Investigating Officer: {investigating_officer}
Action Taken: FIR registered and investigation initiated

The FIR should be professional, complete, and follow standard Indian police FIR format."""
```

**Parameters:**
- Temperature: 0.5 (balanced between consistency and natural language)
- Max tokens: 2048
- Stop sequences: None

#### 4. Prompt Validation

All prompts undergo validation before sending to Claude:

```python
def validate_prompt(prompt: str, max_length: int = 10000) -> bool:
    """
    Validate prompt before sending to Claude.
    
    Checks:
    - Prompt length within limits
    - No PII in system prompts
    - Required placeholders present
    """
    if len(prompt) > max_length:
        raise ValidationError(f"Prompt exceeds max length: {len(prompt)} > {max_length}")
    
    # Check for required placeholders
    required_placeholders = extract_placeholders(prompt)
    if not all(placeholder in prompt for placeholder in required_placeholders):
        raise ValidationError("Missing required placeholders in prompt")
    
    return True
```

### Prompt Optimization Strategy

1. **Token Efficiency**: Keep system prompts concise to minimize input token costs
2. **Determinism**: Use low temperature (0.1-0.3) for structured outputs
3. **Format Enforcement**: Use JSON mode or explicit format instructions
4. **Context Window**: Monitor total tokens (input + output) to stay within Claude limits
5. **Caching**: Cache system prompts where possible (future optimization)

## Security and IAM Configuration

### IAM Policies

The system uses least-privilege IAM policies for all AWS service access.

#### EC2 Instance Role Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
        "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1"
      ]
    },
    {
      "Sid": "TranscribeAccess",
      "Effect": "Allow",
      "Action": [
        "transcribe:StartTranscriptionJob",
        "transcribe:GetTranscriptionJob",
        "transcribe:DeleteTranscriptionJob"
      ],
      "Resource": "*"
    },
    {
      "Sid": "TextractAccess",
      "Effect": "Allow",
      "Action": [
        "textract:DetectDocumentText",
        "textract:AnalyzeDocument"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::afirgen-models-*/*",
        "arn:aws:s3:::afirgen-temp-*/*",
        "arn:aws:s3:::afirgen-backups-*/*"
      ]
    },
    {
      "Sid": "S3ListBuckets",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::afirgen-models-*",
        "arn:aws:s3:::afirgen-temp-*",
        "arn:aws:s3:::afirgen-backups-*"
      ]
    },
    {
      "Sid": "CloudWatchMetrics",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "cloudwatch:namespace": "AFIRGen/Bedrock"
        }
      }
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/afirgen/*"
    },
    {
      "Sid": "XRayTracing",
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    },
    {
      "Sid": "KMSDecrypt",
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "arn:aws:kms:*:*:key/*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": [
            "s3.*.amazonaws.com",
            "rds.*.amazonaws.com"
          ]
        }
      }
    }
  ]
}
```

#### OpenSearch Serverless Access Policy (if using OpenSearch)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "aoss:APIAccessAll"
      ],
      "Resource": "arn:aws:aoss:*:*:collection/*",
      "Condition": {
        "StringEquals": {
          "aoss:collection": "afirgen-ipc-sections"
        }
      }
    }
  ]
}
```

#### Aurora PostgreSQL Access (if using Aurora pgvector)

Aurora access is controlled through RDS IAM authentication:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds-db:connect"
      ],
      "Resource": "arn:aws:rds-db:*:*:dbuser:*/afirgen_app"
    }
  ]
}
```

### Security Groups

#### EC2 Security Group

```hcl
resource "aws_security_group" "ec2" {
  name        = "afirgen-ec2-sg"
  description = "Security group for AFIRGen EC2 instance"
  vpc_id      = aws_vpc.main.id

  # Inbound rules
  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH from admin IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_ip]
  }

  # Outbound rules
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "afirgen-ec2-sg"
  }
}
```

#### RDS Security Group

```hcl
resource "aws_security_group" "rds" {
  name        = "afirgen-rds-sg"
  description = "Security group for AFIRGen RDS instance"
  vpc_id      = aws_vpc.main.id

  # Inbound rules
  ingress {
    description     = "MySQL from EC2"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  # No outbound rules needed for RDS

  tags = {
    Name = "afirgen-rds-sg"
  }
}
```

#### Vector Database Security Group

```hcl
resource "aws_security_group" "vector_db" {
  name        = "afirgen-vector-db-sg"
  description = "Security group for AFIRGen vector database"
  vpc_id      = aws_vpc.main.id

  # Inbound rules (PostgreSQL or OpenSearch)
  ingress {
    description     = "Database access from EC2"
    from_port       = 5432  # PostgreSQL (or 443 for OpenSearch)
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  tags = {
    Name = "afirgen-vector-db-sg"
  }
}
```

### VPC Endpoints

VPC endpoints reduce data transfer costs and improve security by keeping traffic within AWS network.

```hcl
# Bedrock VPC Endpoint
resource "aws_vpc_endpoint" "bedrock" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.bedrock-runtime"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_1.id, aws_subnet.private_2.id]
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "afirgen-bedrock-endpoint"
  }
}

# Transcribe VPC Endpoint
resource "aws_vpc_endpoint" "transcribe" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.transcribe"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_1.id, aws_subnet.private_2.id]
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "afirgen-transcribe-endpoint"
  }
}

# Textract VPC Endpoint
resource "aws_vpc_endpoint" "textract" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.textract"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_1.id, aws_subnet.private_2.id]
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "afirgen-textract-endpoint"
  }
}

# S3 VPC Endpoint (Gateway type)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = {
    Name = "afirgen-s3-endpoint"
  }
}
```

### Encryption Configuration

#### S3 Bucket Encryption

```hcl
resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.afirgen.arn
    }
    bucket_key_enabled = true
  }
}
```

#### RDS Encryption

```hcl
resource "aws_db_instance" "main" {
  # ... other configuration ...
  
  storage_encrypted = true
  kms_key_id        = aws_kms_key.afirgen.arn
  
  # Enable SSL/TLS
  ca_cert_identifier = "rds-ca-2019"
}
```

#### KMS Key

```hcl
resource "aws_kms_key" "afirgen" {
  description             = "KMS key for AFIRGen encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = {
    Name = "afirgen-kms-key"
  }
}

resource "aws_kms_alias" "afirgen" {
  name          = "alias/afirgen"
  target_key_id = aws_kms_key.afirgen.key_id
}
```

## API Endpoints

### Existing Endpoints (Maintained for Backward Compatibility)

All existing API endpoints remain unchanged to ensure frontend compatibility.

#### 1. Generate FIR from Text

```
POST /api/v1/fir/generate
Content-Type: application/json
Authorization: Bearer <token>

Request Body:
{
  "complaint_text": "string",
  "complainant_name": "string",
  "complainant_address": "string",
  "complainant_phone": "string",
  "station_name": "string",
  "investigating_officer": "string"
}

Response (200 OK):
{
  "fir_number": "FIR-20240115-00123",
  "fir_content": "string",
  "ipc_sections": ["IPC 420", "IPC 406"],
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z"
}

Error Response (400/403/500/503):
{
  "error": {
    "code": "BEDROCK_FAILED",
    "message": "FIR generation failed",
    "details": {},
    "correlation_id": "req-abc-123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### 2. Generate FIR from Audio

```
POST /api/v1/fir/generate/audio
Content-Type: multipart/form-data
Authorization: Bearer <token>

Request Body (multipart):
- audio_file: file (WAV/MP3/MPEG)
- language_code: string (optional, e.g., "hi-IN")
- complainant_name: string
- complainant_address: string
- complainant_phone: string
- station_name: string
- investigating_officer: string

Response (200 OK):
{
  "fir_number": "FIR-20240115-00124",
  "transcript": "string",
  "fir_content": "string",
  "ipc_sections": ["IPC 323", "IPC 504"],
  "status": "pending",
  "created_at": "2024-01-15T10:35:00Z"
}
```

#### 3. Generate FIR from Image

```
POST /api/v1/fir/generate/image
Content-Type: multipart/form-data
Authorization: Bearer <token>

Request Body (multipart):
- image_file: file (JPEG/PNG)
- complainant_name: string
- complainant_address: string
- complainant_phone: string
- station_name: string
- investigating_officer: string

Response (200 OK):
{
  "fir_number": "FIR-20240115-00125",
  "extracted_text": "string",
  "fir_content": "string",
  "ipc_sections": ["IPC 379"],
  "status": "pending",
  "created_at": "2024-01-15T10:40:00Z"
}
```

#### 4. Get FIR by Number

```
GET /api/v1/fir/{fir_number}
Authorization: Bearer <token>

Response (200 OK):
{
  "fir_number": "FIR-20240115-00123",
  "session_id": "sess-abc-123",
  "user_id": "user-456",
  "complaint_text": "string",
  "fir_content": "string",
  "violations_json": "[\"IPC 420\", \"IPC 406\"]",
  "status": "finalized",
  "finalized_at": "2024-01-15T11:00:00Z",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### 5. List FIRs

```
GET /api/v1/fir/list?page=1&limit=20&status=pending
Authorization: Bearer <token>

Response (200 OK):
{
  "firs": [
    {
      "fir_number": "FIR-20240115-00123",
      "status": "pending",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 20
}
```

#### 6. Finalize FIR

```
POST /api/v1/fir/{fir_number}/finalize
Authorization: Bearer <token>

Response (200 OK):
{
  "fir_number": "FIR-20240115-00123",
  "status": "finalized",
  "finalized_at": "2024-01-15T11:00:00Z"
}
```

#### 7. Health Check

```
GET /health

Response (200 OK):
{
  "status": "healthy",
  "services": {
    "bedrock": "healthy",
    "transcribe": "healthy",
    "textract": "healthy",
    "vector_db": "healthy",
    "rds": "healthy"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Rate Limiting

All API endpoints implement rate limiting to prevent abuse:

- **Anonymous requests**: 10 requests/minute
- **Authenticated requests**: 100 requests/minute
- **Admin users**: 1000 requests/minute

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705318200
```

### Authentication

The system uses JWT bearer tokens for authentication:

```python
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Token payload includes:
- `user_id`: User identifier
- `role`: User role (admin, officer, viewer, clerk)
- `exp`: Expiration timestamp
- `iat`: Issued at timestamp

## Cost Estimation

### AWS Service Pricing (us-east-1 region)

#### 1. Amazon Transcribe
- **Pricing**: $0.024 per minute (standard)
- **Indian Languages**: Same pricing as English
- **Estimated Usage**: 100 audio files/day × 5 minutes average = 500 minutes/day
- **Daily Cost**: 500 × $0.024 = $12.00/day
- **Monthly Cost**: $360/month

#### 2. Amazon Textract
- **Pricing**: $0.0015 per page (DetectDocumentText)
- **Estimated Usage**: 50 documents/day × 2 pages average = 100 pages/day
- **Daily Cost**: 100 × $0.0015 = $0.15/day
- **Monthly Cost**: $4.50/month

#### 3. Amazon Bedrock - Claude 3 Sonnet
- **Input Tokens**: $0.003 per 1K tokens
- **Output Tokens**: $0.015 per 1K tokens
- **Estimated Usage per FIR**:
  - Legal narrative: 500 input + 200 output = $0.0045
  - Metadata extraction: 200 input + 100 output = $0.0021
  - FIR generation: 1000 input + 1500 output = $0.0255
  - Total per FIR: $0.0321
- **Daily Cost**: 150 FIRs/day × $0.0321 = $4.82/day
- **Monthly Cost**: $144.60/month

#### 4. Amazon Bedrock - Titan Embeddings
- **Pricing**: $0.0001 per 1K input tokens
- **Estimated Usage**: 150 queries/day × 100 tokens = 15K tokens/day
- **Daily Cost**: 15 × $0.0001 = $0.0015/day
- **Monthly Cost**: $0.045/month (negligible)

#### 5. OpenSearch Serverless (if chosen)
- **OCU Pricing**: $0.24 per OCU-hour
- **Minimum**: 2 OCUs (1 indexing + 1 search)
- **Daily Cost**: 2 × 24 × $0.24 = $11.52/day
- **Monthly Cost**: $345.60/month

#### 6. Aurora PostgreSQL with pgvector (if chosen)
- **Serverless v2 ACU**: $0.12 per ACU-hour
- **Minimum**: 0.5 ACU
- **Daily Cost**: 0.5 × 24 × $0.12 = $1.44/day
- **Monthly Cost**: $43.20/month

#### 7. EC2 t3.small
- **Pricing**: $0.0208 per hour
- **Daily Cost**: 24 × $0.0208 = $0.50/day
- **Monthly Cost**: $15/month

#### 8. S3 Storage
- **Standard Storage**: $0.023 per GB/month
- **Estimated Usage**: 10 GB (temporary files, models)
- **Monthly Cost**: 10 × $0.023 = $0.23/month

#### 9. RDS MySQL (existing)
- **db.t3.micro**: $0.017 per hour (free tier eligible)
- **Monthly Cost**: $12.24/month (or $0 with free tier)

### Total Cost Comparison

#### Bedrock Architecture (with Aurora pgvector - recommended)
| Service | Monthly Cost |
|---------|--------------|
| Transcribe | $360.00 |
| Textract | $4.50 |
| Bedrock Claude | $144.60 |
| Bedrock Titan | $0.05 |
| Aurora pgvector | $43.20 |
| EC2 t3.small | $15.00 |
| S3 | $0.23 |
| RDS MySQL | $12.24 |
| **Total** | **$579.82/month** |

#### Bedrock Architecture (with OpenSearch Serverless)
| Service | Monthly Cost |
|---------|--------------|
| Transcribe | $360.00 |
| Textract | $4.50 |
| Bedrock Claude | $144.60 |
| Bedrock Titan | $0.05 |
| OpenSearch | $345.60 |
| EC2 t3.small | $15.00 |
| S3 | $0.23 |
| RDS MySQL | $12.24 |
| **Total** | **$882.22/month** |

#### GGUF Architecture (current)
| Service | Monthly Cost |
|---------|--------------|
| EC2 g5.2xlarge | $871.20 (24/7) |
| S3 | $0.23 |
| RDS MySQL | $12.24 |
| **Total** | **$883.67/month** |

### Cost Savings

**Bedrock with Aurora pgvector vs GGUF:**
- Savings: $883.67 - $579.82 = **$303.85/month (34% reduction)**
- Annual savings: **$3,646.20**

**Additional Savings with On-Demand Usage:**
If the system is only used during business hours (8 hours/day, 5 days/week):
- EC2 savings: $15 × (160/720) = $3.33/month
- Aurora savings: $43.20 × (160/720) = $9.60/month
- Total monthly cost: ~$567/month
- Additional savings: ~$13/month

### Cost Optimization Recommendations

1. **Use Aurora pgvector instead of OpenSearch** - saves $302.40/month
2. **Enable S3 lifecycle policies** - delete temp files after 1 day
3. **Implement aggressive caching** - reduce embedding API calls by 30-50%
4. **Batch processing** - group similar requests to optimize API calls
5. **Use Aurora Serverless v2 auto-scaling** - scale down during low usage
6. **Monitor and optimize prompt lengths** - reduce Bedrock token costs
7. **Consider Reserved Instances for EC2** - save 30-40% on compute costs

## Error Handling

### Error Categories

The system handles four categories of errors:

1. **Client Errors (4xx)**: Invalid input, authentication failures, validation errors
2. **Service Errors (5xx)**: AWS service failures, database errors, internal errors
3. **Throttling Errors (429)**: Rate limit exceeded, quota exceeded
4. **Transient Errors**: Network timeouts, temporary unavailability

### Error Handling Strategy

#### 1. Retry Logic

All AWS service calls implement retry logic with exponential backoff:

```python
async def retry_with_backoff(
    func: Callable,
    max_retries: int = 2,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> Any:
    """
    Retry function with exponential backoff and jitter.
    
    Backoff formula: delay = min(base_delay * (2 ** attempt) + jitter, max_delay)
    where jitter = random.uniform(0, base_delay)
    """
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except (ThrottlingException, ServiceUnavailable) as e:
            if attempt == max_retries:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, base_delay)
            await asyncio.sleep(delay + jitter)
```

Retryable errors:
- `ThrottlingException`, `TooManyRequestsException` (429)
- `ServiceUnavailable`, `InternalServerError` (5xx)
- `RequestTimeout`, `ConnectionError` (network)

Non-retryable errors:
- `ValidationException` (400)
- `AccessDeniedException` (403)
- `ResourceNotFoundException` (404)

#### 2. Circuit Breaker Pattern

Each AWS service has a dedicated circuit breaker:

```python
class CircuitBreaker:
    """
    Circuit breaker states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is down, fail fast
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
```

State transitions:
- CLOSED → OPEN: After `failure_threshold` consecutive failures
- OPEN → HALF_OPEN: After `recovery_timeout` seconds
- HALF_OPEN → CLOSED: After `half_open_max_calls` successful requests
- HALF_OPEN → OPEN: After any failure

#### 3. Error Response Format

All errors return consistent JSON format:

```json
{
  "error": {
    "code": "TRANSCRIBE_FAILED",
    "message": "Audio transcription failed after 2 retries",
    "details": {
      "service": "transcribe",
      "job_name": "transcribe-job-123",
      "reason": "ThrottlingException: Rate exceeded"
    },
    "correlation_id": "req-abc-123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

Error codes:
- `VALIDATION_ERROR`: Invalid input (400)
- `AUTHENTICATION_ERROR`: IAM permission denied (403)
- `TRANSCRIBE_FAILED`: Transcription service error (503)
- `TEXTRACT_FAILED`: OCR service error (503)
- `BEDROCK_FAILED`: LLM inference error (503)
- `VECTOR_DB_FAILED`: Vector database error (503)
- `SERVICE_UNAVAILABLE`: Circuit breaker open (503)
- `INTERNAL_ERROR`: Unexpected error (500)

#### 4. Graceful Degradation

When non-critical services fail:

- **Cache Miss**: If cache lookup fails, proceed with vector search
- **Metrics Emission**: If CloudWatch metrics fail, log locally and continue
- **X-Ray Tracing**: If tracing fails, log warning and continue
- **Cleanup Failure**: If S3 file deletion fails, log error but return success

Critical failures that abort the request:
- Bedrock inference failures (core functionality)
- Vector database unavailable (required for RAG)
- MySQL RDS unavailable (cannot store FIR)

#### 5. Timeout Configuration

Service-specific timeouts prevent indefinite blocking:

```python
TIMEOUTS = {
    'transcribe_job_poll': 180,  # 3 minutes
    'textract_detect': 30,       # 30 seconds
    'bedrock_invoke': 60,        # 1 minute
    'vector_search': 10,         # 10 seconds
    's3_upload': 30,             # 30 seconds
    'rds_query': 5,              # 5 seconds
}
```

#### 6. Error Logging

All errors are logged with structured context:

```python
logger.error(
    "AWS service call failed",
    extra={
        "service": "bedrock",
        "operation": "invoke_model",
        "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
        "error_code": "ThrottlingException",
        "error_message": "Rate limit exceeded",
        "correlation_id": correlation_id,
        "retry_attempt": attempt,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }
)
```


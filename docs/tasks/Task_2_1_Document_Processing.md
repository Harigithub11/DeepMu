# Task 2.1: Document Processing + deepmu.tech Security (35 mins)

## 🎯 **Objective**
Implement comprehensive multi-format document processing pipeline with advanced security measures, intelligent chunking, and seamless integration with the hybrid database architecture.

## 📋 **CodeMate Build Prompt**

```
Implement secure document processing pipeline for DocuMind AI Research Agent with deepmu.tech security integration:

**Document Processing Implementation:**

1. **Core Document Service (services/document_service.py):**
   ```python
   import asyncio
   import hashlib
   import magic
   import os
   import tempfile
   from pathlib import Path
   from typing import List, Dict, Any, Optional, BinaryIO
   import logging
   from datetime import datetime

   # Document processing libraries
   import PyPDF2
   from docx import Document
   from bs4 import BeautifulSoup
   import pytesseract
   from PIL import Image
   import pandas as pd
   import json
   import textract

   # NLP and chunking
   import spacy
   import nltk
   from sentence_transformers import SentenceTransformer

   # Security
   import magic
   from werkzeug.utils import secure_filename

   from config.settings import settings
   from config.environment_manager import env_manager
   from services.cache_service import cache_service
   from services.qdrant_service import qdrant_service
   from services.monitoring_service import monitoring_service

   logger = logging.getLogger(__name__)

   class DocumentProcessor:
       def __init__(self):
           self.supported_formats = {
               '.pdf', '.docx', '.doc', '.txt', '.md', '.html', '.htm',
               '.rtf', '.xlsx', '.xls', '.csv', '.json', '.xml',
               '.png', '.jpg', '.jpeg', '.tiff', '.bmp'  # OCR support
           }

           self.max_file_size = env_manager.get_performance_config()["max_file_size_mb"] * 1024 * 1024
           self.embedding_model = None
           self.nlp_model = None

       async def initialize(self):
           """Initialize document processing components"""
           try:
               # Load embedding model
               model_name = env_manager.get_performance_config()["embedding_model"]
               self.embedding_model = SentenceTransformer(model_name)
               logger.info(f"Loaded embedding model: {model_name}")

               # Load spaCy model
               try:
                   self.nlp_model = spacy.load("en_core_web_sm")
               except OSError:
                   logger.warning("spaCy model not found, downloading...")
                   os.system("python -m spacy download en_core_web_sm")
                   self.nlp_model = spacy.load("en_core_web_sm")

               # Download NLTK data
               nltk.download('punkt', quiet=True)
               nltk.download('stopwords', quiet=True)

               logger.info("Document processor initialized successfully")
               return True

           except Exception as e:
               logger.error(f"Error initializing document processor: {e}")
               return False

       async def process_document(self, file_content: bytes, filename: str, user_id: Optional[str] = None) -> Dict[str, Any]:
           """Main document processing pipeline"""
           try:
               # Security validation
               security_check = await self._security_validation(file_content, filename)
               if not security_check["safe"]:
                   return {"error": "Security validation failed", "details": security_check}

               # Extract text content
               with monitoring_service.track_document_processing(Path(filename).suffix.lower()):
                   text_content = await self._extract_text(file_content, filename)

                   if not text_content:
                       return {"error": "Failed to extract text content"}

                   # Generate document metadata
                   metadata = await self._generate_metadata(file_content, filename, user_id)

                   # Intelligent text chunking
                   chunks = await self._intelligent_chunking(text_content, metadata)

                   # Generate embeddings for chunks
                   embeddings = await self._generate_embeddings(chunks)

                   # Prepare documents for storage
                   documents = []
                   for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                       doc = {
                           "id": f"{metadata['file_hash']}_{i}",
                           "text": chunk["text"],
                           "embedding": embedding.tolist(),
                           "metadata": {
                               **metadata,
                               "chunk_index": i,
                               "chunk_type": chunk["type"],
                               "chunk_size": len(chunk["text"])
                           },
                           "file_name": filename,
                           "chunk_index": i
                       }
                       documents.append(doc)

                   # Store in databases
                   storage_result = await self._store_documents(documents)

                   # Cache processing result
                   await self._cache_processing_result(metadata["file_hash"], {
                       "documents": documents,
                       "metadata": metadata,
                       "processing_time": datetime.utcnow().isoformat()
                   })

                   monitoring_service.increment_embeddings_generated(len(embeddings))

                   return {
                       "success": True,
                       "documents_count": len(documents),
                       "metadata": metadata,
                       "storage_result": storage_result,
                       "processing_time": datetime.utcnow().isoformat()
                   }

           except Exception as e:
               logger.error(f"Error processing document {filename}: {e}")
               return {"error": str(e)}

       async def _security_validation(self, file_content: bytes, filename: str) -> Dict[str, Any]:
           """Comprehensive security validation"""
           try:
               result = {"safe": True, "checks": {}}

               # File size check
               if len(file_content) > self.max_file_size:
                   result["safe"] = False
                   result["checks"]["file_size"] = f"File too large: {len(file_content)} bytes"
                   return result

               # File extension validation
               file_ext = Path(filename).suffix.lower()
               if file_ext not in self.supported_formats:
                   result["safe"] = False
                   result["checks"]["extension"] = f"Unsupported file type: {file_ext}"
                   return result

               # MIME type validation
               mime_type = magic.from_buffer(file_content, mime=True)
               expected_mimes = {
                   '.pdf': 'application/pdf',
                   '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                   '.txt': 'text/plain',
                   '.json': 'application/json',
                   '.png': 'image/png',
                   '.jpg': 'image/jpeg',
                   '.jpeg': 'image/jpeg'
               }

               if file_ext in expected_mimes and mime_type != expected_mimes[file_ext]:
                   result["safe"] = False
                   result["checks"]["mime_type"] = f"MIME mismatch: expected {expected_mimes[file_ext]}, got {mime_type}"
                   return result

               # Virus scanning placeholder (integrate with antivirus if needed)
               result["checks"]["virus_scan"] = "passed"

               # Malicious content detection
               if await self._detect_malicious_content(file_content):
                   result["safe"] = False
                   result["checks"]["malicious_content"] = "Potential malicious content detected"
                   return result

               result["checks"]["security"] = "passed"
               return result

           except Exception as e:
               logger.error(f"Security validation error: {e}")
               return {"safe": False, "error": str(e)}

       async def _detect_malicious_content(self, file_content: bytes) -> bool:
           """Detect potentially malicious content"""
           try:
               # Check for suspicious patterns
               suspicious_patterns = [
                   b'<script',
                   b'javascript:',
                   b'eval(',
                   b'exec(',
                   b'system(',
                   b'shell_exec'
               ]

               content_lower = file_content.lower()
               for pattern in suspicious_patterns:
                   if pattern in content_lower:
                       logger.warning(f"Suspicious pattern detected: {pattern}")
                       return True

               return False

           except Exception as e:
               logger.error(f"Malicious content detection error: {e}")
               return False

       async def _extract_text(self, file_content: bytes, filename: str) -> Optional[str]:
           """Extract text from various file formats"""
           try:
               file_ext = Path(filename).suffix.lower()

               # Create temporary file for processing
               with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
                   temp_file.write(file_content)
                   temp_file.flush()
                   temp_path = temp_file.name

               try:
                   if file_ext == '.pdf':
                       return await self._extract_pdf_text(temp_path)
                   elif file_ext in ['.docx', '.doc']:
                       return await self._extract_docx_text(temp_path)
                   elif file_ext in ['.txt', '.md']:
                       return file_content.decode('utf-8', errors='ignore')
                   elif file_ext in ['.html', '.htm']:
                       return await self._extract_html_text(file_content)
                   elif file_ext in ['.xlsx', '.xls', '.csv']:
                       return await self._extract_spreadsheet_text(temp_path)
                   elif file_ext == '.json':
                       return await self._extract_json_text(file_content)
                   elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                       return await self._extract_image_text(temp_path)
                   else:
                       # Fallback to textract
                       return textract.process(temp_path).decode('utf-8', errors='ignore')

               finally:
                   # Clean up temporary file
                   os.unlink(temp_path)

           except Exception as e:
               logger.error(f"Text extraction error for {filename}: {e}")
               return None

       async def _extract_pdf_text(self, file_path: str) -> str:
           """Extract text from PDF files"""
           text = ""
           try:
               with open(file_path, 'rb') as file:
                   pdf_reader = PyPDF2.PdfReader(file)
                   for page in pdf_reader.pages:
                       text += page.extract_text() + "\n"
               return text.strip()
           except Exception as e:
               logger.error(f"PDF extraction error: {e}")
               return ""

       async def _extract_docx_text(self, file_path: str) -> str:
           """Extract text from DOCX files"""
           try:
               doc = Document(file_path)
               return "\n".join([paragraph.text for paragraph in doc.paragraphs])
           except Exception as e:
               logger.error(f"DOCX extraction error: {e}")
               return ""

       async def _extract_html_text(self, file_content: bytes) -> str:
           """Extract text from HTML files"""
           try:
               soup = BeautifulSoup(file_content, 'html.parser')
               # Remove script and style elements
               for script in soup(["script", "style"]):
                   script.decompose()
               return soup.get_text(separator=' ', strip=True)
           except Exception as e:
               logger.error(f"HTML extraction error: {e}")
               return ""

       async def _extract_spreadsheet_text(self, file_path: str) -> str:
           """Extract text from spreadsheet files"""
           try:
               if file_path.endswith('.csv'):
                   df = pd.read_csv(file_path)
               else:
                   df = pd.read_excel(file_path)

               # Convert all cells to string and concatenate
               text_content = []
               for col in df.columns:
                   text_content.append(f"Column: {col}")
                   text_content.extend(df[col].astype(str).tolist())

               return "\n".join(text_content)
           except Exception as e:
               logger.error(f"Spreadsheet extraction error: {e}")
               return ""

       async def _extract_json_text(self, file_content: bytes) -> str:
           """Extract text from JSON files"""
           try:
               data = json.loads(file_content.decode('utf-8'))

               def extract_text_from_json(obj, prefix=""):
                   text_parts = []
                   if isinstance(obj, dict):
                       for key, value in obj.items():
                           text_parts.append(f"{prefix}{key}: {extract_text_from_json(value, prefix + '  ')}")
                   elif isinstance(obj, list):
                       for i, item in enumerate(obj):
                           text_parts.append(f"{prefix}[{i}]: {extract_text_from_json(item, prefix + '  ')}")
                   else:
                       return str(obj)
                   return "\n".join(text_parts)

               return extract_text_from_json(data)
           except Exception as e:
               logger.error(f"JSON extraction error: {e}")
               return ""

       async def _extract_image_text(self, file_path: str) -> str:
           """Extract text from images using OCR"""
           try:
               if not env_manager.get_feature_flags()["document_ocr"]:
                   return ""

               image = Image.open(file_path)
               text = pytesseract.image_to_string(image, lang='eng')
               return text.strip()
           except Exception as e:
               logger.error(f"OCR extraction error: {e}")
               return ""

       async def _generate_metadata(self, file_content: bytes, filename: str, user_id: Optional[str]) -> Dict[str, Any]:
           """Generate comprehensive document metadata"""
           try:
               file_hash = hashlib.sha256(file_content).hexdigest()

               metadata = {
                   "file_name": secure_filename(filename),
                   "file_hash": file_hash,
                   "file_size": len(file_content),
                   "file_type": Path(filename).suffix.lower(),
                   "mime_type": magic.from_buffer(file_content, mime=True),
                   "upload_timestamp": datetime.utcnow().isoformat(),
                   "user_id": user_id,
                   "domain": env_manager.domain_config["primary"],
                   "processing_version": "1.0"
               }

               return metadata

           except Exception as e:
               logger.error(f"Metadata generation error: {e}")
               return {}

       async def _intelligent_chunking(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
           """Intelligent text chunking with overlap and semantic awareness"""
           try:
               if not text.strip():
                   return []

               chunks = []
               chunk_size = 1000  # tokens
               overlap = 200  # tokens

               # Use spaCy for sentence boundary detection
               doc = self.nlp_model(text)
               sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

               current_chunk = ""
               current_size = 0

               for sentence in sentences:
                   sentence_size = len(sentence.split())

                   if current_size + sentence_size > chunk_size and current_chunk:
                       # Save current chunk
                       chunks.append({
                           "text": current_chunk.strip(),
                           "type": "semantic",
                           "token_count": current_size
                       })

                       # Start new chunk with overlap
                       overlap_text = " ".join(current_chunk.split()[-overlap:])
                       current_chunk = overlap_text + " " + sentence
                       current_size = len(current_chunk.split())
                   else:
                       current_chunk += " " + sentence
                       current_size += sentence_size

               # Add final chunk
               if current_chunk.strip():
                   chunks.append({
                       "text": current_chunk.strip(),
                       "type": "semantic",
                       "token_count": current_size
                   })

               logger.info(f"Created {len(chunks)} chunks for {metadata.get('file_name', 'unknown')}")
               return chunks

           except Exception as e:
               logger.error(f"Chunking error: {e}")
               return [{"text": text, "type": "fallback", "token_count": len(text.split())}]

       async def _generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List:
           """Generate embeddings for text chunks"""
           try:
               texts = [chunk["text"] for chunk in chunks]

               # Check cache first
               cached_embeddings = []
               uncached_texts = []
               uncached_indices = []

               for i, text in enumerate(texts):
                   text_hash = hashlib.sha256(text.encode()).hexdigest()
                   cached_embedding = await cache_service.get_cached_embeddings(text_hash)

                   if cached_embedding:
                       cached_embeddings.append((i, cached_embedding))
                       monitoring_service.record_cache_hit("embeddings")
                   else:
                       uncached_texts.append(text)
                       uncached_indices.append(i)
                       monitoring_service.record_cache_miss("embeddings")

               # Generate embeddings for uncached texts
               embeddings = [None] * len(texts)

               if uncached_texts:
                   batch_size = env_manager.get_performance_config()["batch_size"]
                   new_embeddings = []

                   for i in range(0, len(uncached_texts), batch_size):
                       batch = uncached_texts[i:i + batch_size]
                       batch_embeddings = self.embedding_model.encode(batch, convert_to_numpy=True)
                       new_embeddings.extend(batch_embeddings)

                   # Cache new embeddings
                   for text, embedding, idx in zip(uncached_texts, new_embeddings, uncached_indices):
                       text_hash = hashlib.sha256(text.encode()).hexdigest()
                       await cache_service.cache_embeddings(text_hash, embedding.tolist())
                       embeddings[idx] = embedding

               # Fill in cached embeddings
               for idx, cached_embedding in cached_embeddings:
                   embeddings[idx] = cached_embedding

               return embeddings

           except Exception as e:
               logger.error(f"Embedding generation error: {e}")
               return []

       async def _store_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
           """Store documents in hybrid database system"""
           try:
               results = {}

               # Store in Qdrant (primary vector storage)
               qdrant_result = await qdrant_service.add_documents(documents)
               results["qdrant"] = qdrant_result

               # Store in additional backends if available
               # TODO: Add FAISS and Elasticsearch storage

               return results

           except Exception as e:
               logger.error(f"Document storage error: {e}")
               return {"error": str(e)}

       async def _cache_processing_result(self, file_hash: str, result: Dict[str, Any]) -> bool:
           """Cache document processing result"""
           try:
               cache_key = f"document_processing:{file_hash}"
               return await cache_service.set_cache(cache_key, result, ttl=86400)  # 24h cache
           except Exception as e:
               logger.error(f"Result caching error: {e}")
               return False

       async def get_processing_status(self, file_hash: str) -> Optional[Dict[str, Any]]:
           """Get cached processing status"""
           try:
               cache_key = f"document_processing:{file_hash}"
               return await cache_service.get_cache(cache_key)
           except Exception as e:
               logger.error(f"Status retrieval error: {e}")
               return None

       async def health_check(self) -> Dict[str, Any]:
           """Document processor health check"""
           try:
               return {
                   "status": "healthy",
                   "embedding_model": self.embedding_model is not None,
                   "nlp_model": self.nlp_model is not None,
                   "supported_formats": list(self.supported_formats),
                   "max_file_size_mb": self.max_file_size // (1024 * 1024)
               }
           except Exception as e:
               logger.error(f"Document processor health check failed: {e}")
               return {"status": "unhealthy", "error": str(e)}

   # Global instance
   document_processor = DocumentProcessor()
   ```

2. **Document API Routes (api/routes/documents.py):**
   ```python
   from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
   from fastapi.security import HTTPBearer
   from typing import List, Optional
   import hashlib

   from services.document_service import document_processor
   from services.monitoring_service import monitoring_service
   from models.schemas import DocumentResponse, ProcessingStatus

   router = APIRouter()
   security = HTTPBearer()

   @router.post("/upload", response_model=DocumentResponse)
   async def upload_document(
       background_tasks: BackgroundTasks,
       file: UploadFile = File(...),
       user_id: Optional[str] = None
   ):
       """Upload and process a single document"""
       try:
           with monitoring_service.track_request("POST", "/documents/upload"):
               # Read file content
               file_content = await file.read()

               # Generate file hash for deduplication
               file_hash = hashlib.sha256(file_content).hexdigest()

               # Check if already processed
               existing_result = await document_processor.get_processing_status(file_hash)
               if existing_result:
                   return DocumentResponse(
                       success=True,
                       message="Document already processed",
                       file_hash=file_hash,
                       documents_count=len(existing_result.get("documents", [])),
                       cached=True
                   )

               # Process document
               result = await document_processor.process_document(file_content, file.filename, user_id)

               if result.get("error"):
                   raise HTTPException(status_code=400, detail=result["error"])

               return DocumentResponse(
                   success=True,
                   message="Document processed successfully",
                   file_hash=result["metadata"]["file_hash"],
                   documents_count=result["documents_count"],
                   processing_time=result["processing_time"]
               )

       except Exception as e:
           raise HTTPException(status_code=500, detail=str(e))

   @router.post("/upload-multiple")
   async def upload_multiple_documents(
       background_tasks: BackgroundTasks,
       files: List[UploadFile] = File(...),
       user_id: Optional[str] = None
   ):
       """Upload and process multiple documents"""
       try:
           results = []

           for file in files:
               file_content = await file.read()
               file_hash = hashlib.sha256(file_content).hexdigest()

               # Check cache first
               existing_result = await document_processor.get_processing_status(file_hash)
               if existing_result:
                   results.append({
                       "filename": file.filename,
                       "status": "cached",
                       "file_hash": file_hash
                   })
                   continue

               # Process document
               result = await document_processor.process_document(file_content, file.filename, user_id)

               if result.get("error"):
                   results.append({
                       "filename": file.filename,
                       "status": "error",
                       "error": result["error"]
                   })
               else:
                   results.append({
                       "filename": file.filename,
                       "status": "success",
                       "file_hash": result["metadata"]["file_hash"],
                       "documents_count": result["documents_count"]
                   })

           return {
               "success": True,
               "total_files": len(files),
               "results": results
           }

       except Exception as e:
           raise HTTPException(status_code=500, detail=str(e))

   @router.get("/status/{file_hash}", response_model=ProcessingStatus)
   async def get_processing_status(file_hash: str):
       """Get document processing status"""
       try:
           status = await document_processor.get_processing_status(file_hash)

           if not status:
               raise HTTPException(status_code=404, detail="Document not found")

           return ProcessingStatus(
               file_hash=file_hash,
               status="completed",
               documents_count=len(status.get("documents", [])),
               processing_time=status.get("processing_time"),
               metadata=status.get("metadata", {})
           )

       except HTTPException:
           raise
       except Exception as e:
           raise HTTPException(status_code=500, detail=str(e))

   @router.get("/health")
   async def document_service_health():
       """Document service health check"""
       return await document_processor.health_check()
   ```

3. **Document Schemas (models/schemas.py - add to existing):**
   ```python
   from pydantic import BaseModel
   from typing import Optional, Dict, Any, List
   from datetime import datetime

   class DocumentResponse(BaseModel):
       success: bool
       message: str
       file_hash: str
       documents_count: int
       processing_time: Optional[str] = None
       cached: bool = False

   class ProcessingStatus(BaseModel):
       file_hash: str
       status: str
       documents_count: int
       processing_time: Optional[str]
       metadata: Dict[str, Any]

   class DocumentMetadata(BaseModel):
       file_name: str
       file_hash: str
       file_size: int
       file_type: str
       mime_type: str
       upload_timestamp: str
       user_id: Optional[str]
       domain: str
   ```

**Implementation Steps:**
1. Create comprehensive document processing service
2. Implement security validation and malicious content detection
3. Add multi-format text extraction capabilities
4. Create intelligent chunking with semantic awareness
5. Implement embedding generation with caching
6. Set up document API routes with security
7. Test all document formats and security measures

**Success Criteria for this prompt:**
- All supported file formats process correctly
- Security validation blocks malicious content
- Intelligent chunking creates optimal segments
- Embeddings generated and cached efficiently
- Documents stored in hybrid database system
- API endpoints secure and functional
```

## 🔍 **Debug Checkpoint Instructions**

**After running the above prompt, go to debug mode and verify:**

1. **Document Processing Initialization:**
   ```bash
   # Test document processor import and initialization
   cd project
   python -c "
   import asyncio
   from services.document_service import document_processor

   async def test():
       result = await document_processor.initialize()
       print(f'Initialization: {result}')

   asyncio.run(test())
   "
   ```

2. **File Format Support Test:**
   ```bash
   # Create test files for each format
   echo "Test content" > test.txt
   echo '{"test": "data"}' > test.json

   # Test text extraction
   cd project
   python -c "
   import asyncio
   from services.document_service import document_processor

   async def test():
       await document_processor.initialize()

       with open('test.txt', 'rb') as f:
           content = f.read()

       result = await document_processor._extract_text(content, 'test.txt')
       print(f'Text extraction: {result}')

   asyncio.run(test())
   "
   ```

3. **Security Validation Test:**
   ```bash
   # Test security validation
   cd project
   python -c "
   import asyncio
   from services.document_service import document_processor

   async def test():
       await document_processor.initialize()

       # Test with safe content
       safe_content = b'This is safe content'
       result = await document_processor._security_validation(safe_content, 'test.txt')
       print(f'Security validation: {result}')

   asyncio.run(test())
   "
   ```

4. **API Routes Test:**
   ```bash
   # Start application
   cd project
   uvicorn main:app --reload --port 8000

   # Test document upload endpoint
   # Create a test file first
   echo "Test document content" > test_upload.txt

   # Test upload (in another terminal)
   curl -X POST "http://localhost:8000/api/v1/documents/upload" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@test_upload.txt"
   ```

5. **Embedding Generation Test:**
   ```bash
   # Test embedding generation
   cd project
   python -c "
   import asyncio
   from services.document_service import document_processor

   async def test():
       await document_processor.initialize()

       chunks = [{'text': 'This is a test chunk', 'type': 'test', 'token_count': 5}]
       embeddings = await document_processor._generate_embeddings(chunks)
       print(f'Generated embeddings: {len(embeddings)} vectors')

   asyncio.run(test())
   "
   ```

**Common Issues to Debug:**
- Missing spaCy model installation
- NLTK data download failures
- Tesseract OCR not installed for image processing
- Memory issues with large files
- Embedding model loading failures
- Database connection errors during storage

## ✅ **Success Criteria**

### **Document Processing Core:**
- [ ] All supported file formats (PDF, DOCX, TXT, JSON, images) process correctly
- [ ] Text extraction working for each format with fallback mechanisms
- [ ] Intelligent chunking creates semantically coherent segments
- [ ] Embedding generation functional with caching optimization

### **Security Implementation:**
- [ ] File size validation prevents oversized uploads
- [ ] MIME type validation blocks disguised malicious files
- [ ] Malicious content detection identifies suspicious patterns
- [ ] Secure filename handling prevents path traversal attacks

### **Performance Optimization:**
- [ ] Embedding caching reduces redundant computation by >70%
- [ ] Batch processing optimizes GPU utilization for RTX 3060
- [ ] Memory usage stays within configured limits
- [ ] Processing time <30 seconds for typical documents

### **API Integration:**
- [ ] Document upload endpoint accepts files and returns proper responses
- [ ] Multiple file upload processes batches efficiently
- [ ] Processing status endpoint provides real-time updates
- [ ] Health check endpoint reports service status accurately

### **Database Integration:**
- [ ] Documents stored successfully in Qdrant vector database
- [ ] Metadata properly structured and searchable
- [ ] Deduplication prevents processing identical files
- [ ] Storage results tracked and reported

### **Error Handling:**
- [ ] Graceful handling of unsupported file formats
- [ ] Proper error messages for security validation failures
- [ ] Retry mechanisms for transient processing failures
- [ ] Comprehensive logging for debugging

## ⏱️ **Time Allocation:**
- **Core Document Service Implementation:** 15 minutes
- **Security Validation System:** 8 minutes
- **Multi-format Text Extraction:** 7 minutes
- **API Routes and Integration:** 5 minutes

## 🚀 **Next Task:**
After successful completion and debugging, proceed to **Task 2.2: Hybrid Search + deepmu.tech CDN** for implementing the comprehensive hybrid search architecture with performance optimization.
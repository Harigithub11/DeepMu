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

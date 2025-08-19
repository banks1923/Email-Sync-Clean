#!/usr/bin/env python3
"""
Vector System Debugging and Fix Script
Diagnoses and resolves vector database issues in the email sync system
"""

import os
import sys
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

# Import system modules
try:
    from vector_service.config import VectorConfig
    from vector_service.database import EmailDatabase
    from vector_service.embeddings import EmbedderFactory
    from vector_service.qdrant import QdrantManager
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)

class VectorDebugger:
    """Comprehensive vector system debugger and fixer"""
    
    def __init__(self):
        self.issues = []
        self.fixes_applied = []
        self.config = None
        self.db_path = "emails.db"
        
    def run_diagnosis(self) -> Dict[str, Any]:
        """Run complete system diagnosis"""
        print("\n" + "="*60)
        print("🔍 VECTOR SYSTEM DIAGNOSTIC")
        print("="*60)
        
        # Check 1: Environment Variables
        self.check_environment()
        
        # Check 2: Configuration
        self.check_configuration()
        
        # Check 3: Database Tables
        self.check_database_tables()
        
        # Check 4: Legal BERT Model
        self.check_legal_bert_model()
        
        # Check 5: Qdrant Collection
        self.check_qdrant_collection()
        
        # Check 6: Test Embedding Generation
        self.test_embedding_generation()
        
        return {
            "issues": self.issues,
            "fixes_applied": self.fixes_applied
        }
    
    def check_environment(self):
        """Check environment variables"""
        print("\n📋 Checking Environment Variables...")
        
        env_vars = {
            "EMBEDDING_PROVIDER": os.getenv("EMBEDDING_PROVIDER", "NOT SET"),
            "EMBEDDING_DIMENSIONS": os.getenv("EMBEDDING_DIMENSIONS", "NOT SET"),
            "LEGAL_BERT_MODEL_PATH": os.getenv("LEGAL_BERT_MODEL_PATH", "NOT SET"),
            "LEGAL_BERT_ENABLED": os.getenv("LEGAL_BERT_ENABLED", "NOT SET"),
        }
        
        for key, value in env_vars.items():
            if value == "NOT SET":
                print(f"  ⚠️  {key}: Not configured")
                self.issues.append(f"Missing env var: {key}")
            else:
                print(f"  ✅ {key}: {value}")
        
        # Check for problematic OpenAI configuration
        if os.getenv("OPENAI_API_KEY"):
            print(f"  ⚠️  OPENAI_API_KEY is set but system requires Legal BERT")
            self.issues.append("OpenAI API key present but Legal BERT is mandated")
    
    def check_configuration(self):
        """Check VectorConfig validation"""
        print("\n🔧 Checking Configuration...")
        
        try:
            self.config = VectorConfig(load_env_file=True)
            validation = self.config.validate()
            
            if validation["success"]:
                print(f"  ✅ Configuration valid")
                print(f"     Provider: {self.config.embedding_provider}")
                print(f"     Dimensions: {self.config.embedding_dimensions}")
                print(f"     Model: {self.config.legal_bert_model_path}")
            else:
                print(f"  ❌ Configuration invalid: {validation['error']}")
                self.issues.append(f"Config validation failed: {validation['error']}")
                
                # Check if it's the OpenAI restriction
                if "NOT AUTHORIZED" in validation['error']:
                    self.fix_provider_configuration()
                    
        except Exception as e:
            print(f"  ❌ Failed to load configuration: {e}")
            self.issues.append(f"Config load failed: {e}")
    
    def check_database_tables(self):
        """Check if required database tables exist"""
        print("\n💾 Checking Database Tables...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ["emails", "documents"]
            
            for table in required_tables:
                if table in tables:
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"  ✅ Table '{table}' exists ({count} rows)")
                else:
                    print(f"  ❌ Table '{table}' missing")
                    self.issues.append(f"Missing table: {table}")
                    self.create_missing_table(table)
                    
            conn.close()
            
        except Exception as e:
            print(f"  ❌ Database check failed: {e}")
            self.issues.append(f"Database error: {e}")
    
    def check_legal_bert_model(self):
        """Check if Legal BERT model is accessible"""
        print("\n🤖 Checking Legal BERT Model...")
        
        if not self.config:
            print("  ⚠️  Configuration not loaded, skipping model check")
            return
            
        model_path = self.config.legal_bert_model_path
        print(f"  Model path: {model_path}")
        
        # Check if it's a HuggingFace model identifier
        if "/" in model_path:
            print(f"  📦 HuggingFace model: {model_path}")
            # Try to create embedder to verify model loads
            try:
                result = EmbedderFactory.create_embedder(self.config, "legal_bert")
                if result["success"]:
                    print(f"  ✅ Model loaded successfully")
                    print(f"     Dimensions: {result['dimensions']}")
                else:
                    print(f"  ❌ Model load failed: {result['error']}")
                    self.issues.append(f"Legal BERT load failed: {result['error']}")
            except Exception as e:
                print(f"  ❌ Model initialization error: {e}")
                self.issues.append(f"Legal BERT error: {e}")
        else:
            # Check local path
            if os.path.exists(model_path):
                print(f"  ✅ Local model path exists")
            else:
                print(f"  ❌ Local model path not found")
                self.issues.append(f"Model path not found: {model_path}")
    
    def check_qdrant_collection(self):
        """Check Qdrant collection configuration"""
        print("\n🔍 Checking Qdrant Collection...")
        
        if not self.config:
            print("  ⚠️  Configuration not loaded, skipping Qdrant check")
            return
            
        try:
            qdrant = QdrantManager(self.config)
            info = qdrant.get_collection_info()
            
            if info["success"]:
                print(f"  ✅ Collection '{info['name']}' exists")
                print(f"     Vectors: {info['vectors_count']}")
                print(f"     Dimension: {info['config']['vector_size']}")
                print(f"     Distance: {info['config']['distance']}")
                
                # Check dimension match
                expected_dim = self.config.embedding_dimensions
                actual_dim = info['config']['vector_size']
                
                if expected_dim != actual_dim:
                    print(f"  ❌ Dimension mismatch!")
                    print(f"     Expected: {expected_dim} (Legal BERT)")
                    print(f"     Actual: {actual_dim}")
                    self.issues.append(f"Qdrant dimension mismatch: {actual_dim} != {expected_dim}")
                    self.fix_qdrant_collection(qdrant)
                    
            else:
                print(f"  ❌ Collection check failed: {info['error']}")
                self.issues.append(f"Qdrant error: {info['error']}")
                
        except Exception as e:
            print(f"  ❌ Qdrant connection failed: {e}")
            self.issues.append(f"Qdrant connection error: {e}")
    
    def test_embedding_generation(self):
        """Test actual embedding generation"""
        print("\n🧪 Testing Embedding Generation...")
        
        if not self.config:
            print("  ⚠️  Configuration not loaded, skipping embedding test")
            return
            
        try:
            result = EmbedderFactory.create_embedder(self.config, "legal_bert")
            if not result["success"]:
                print(f"  ❌ Embedder creation failed: {result['error']}")
                self.issues.append(f"Embedder creation failed: {result['error']}")
                return
                
            embedder = result["embedder"]
            test_text = "This is a test email about legal compliance and regulatory requirements."
            
            print(f"  Testing with: '{test_text[:50]}...'")
            
            embed_result = embedder.generate_embedding(test_text)
            
            if embed_result["success"]:
                print(f"  ✅ Embedding generated successfully")
                print(f"     Dimensions: {embed_result['dimensions']}")
                print(f"     Model: {embed_result['model']}")
                print(f"     First 5 values: {embed_result['embedding'][:5]}")
            else:
                print(f"  ❌ Embedding generation failed: {embed_result['error']}")
                self.issues.append(f"Embedding generation failed: {embed_result['error']}")
                
        except Exception as e:
            print(f"  ❌ Embedding test error: {e}")
            self.issues.append(f"Embedding test error: {e}")
    
    def create_missing_table(self, table_name: str):
        """Create missing database table"""
        print(f"\n🔨 Creating missing table: {table_name}")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if table_name == "emails":
                cursor.execute("""
                    CREATE TABLE emails (
                        message_id TEXT PRIMARY KEY,
                        sender TEXT NOT NULL,
                        recipient_to TEXT,
                        subject TEXT,
                        content TEXT,
                        datetime_utc TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print(f"  ✅ Created 'emails' table")
                self.fixes_applied.append("Created emails table")
                
            elif table_name == "documents":
                cursor.execute("""
                    CREATE TABLE documents (
                        chunk_id TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        file_name TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        text_content TEXT NOT NULL,
                        char_count INTEGER NOT NULL,
                        file_size INTEGER,
                        modified_time REAL,
                        processed_time TEXT DEFAULT CURRENT_TIMESTAMP,
                        content_type TEXT DEFAULT 'document'
                    )
                """)
                print(f"  ✅ Created 'documents' table")
                self.fixes_applied.append("Created documents table")
                
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"  ❌ Failed to create table: {e}")
    
    def fix_provider_configuration(self):
        """Fix embedding provider configuration"""
        print("\n🔧 Fixing Provider Configuration...")
        
        # Create .env file with correct settings
        env_content = """# Vector Service Configuration
EMBEDDING_PROVIDER=legal_bert
EMBEDDING_DIMENSIONS=1024
LEGAL_BERT_MODEL_PATH=pile-of-law/legalbert-large-1.7M-2
LEGAL_BERT_ENABLED=true
LEGAL_BERT_BATCH_SIZE=32
LEGAL_BERT_MAX_LENGTH=512
"""
        
        try:
            with open(".env", "w") as f:
                f.write(env_content)
            print("  ✅ Created .env file with Legal BERT configuration")
            self.fixes_applied.append("Created .env with Legal BERT config")
        except Exception as e:
            print(f"  ❌ Failed to create .env: {e}")
    
    def fix_qdrant_collection(self, qdrant: QdrantManager):
        """Recreate Qdrant collection with correct dimensions"""
        print("\n🔧 Fixing Qdrant Collection...")
        
        response = input("  ⚠️  Delete and recreate collection? (y/n): ")
        if response.lower() != 'y':
            print("  Skipped collection recreation")
            return
            
        try:
            # Delete existing collection
            delete_result = qdrant.delete_collection()
            if delete_result["success"]:
                print("  ✅ Deleted existing collection")
                
            # Recreate with correct dimensions
            qdrant._ensure_collection()
            print(f"  ✅ Recreated collection with {self.config.embedding_dimensions} dimensions")
            self.fixes_applied.append(f"Recreated Qdrant collection with {self.config.embedding_dimensions}D")
            
        except Exception as e:
            print(f"  ❌ Failed to fix collection: {e}")
    
    def print_summary(self):
        """Print diagnostic summary"""
        print("\n" + "="*60)
        print("📊 DIAGNOSTIC SUMMARY")
        print("="*60)
        
        if not self.issues:
            print("\n✅ No issues found! System is properly configured.")
        else:
            print(f"\n❌ Found {len(self.issues)} issues:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        
        if self.fixes_applied:
            print(f"\n✅ Applied {len(self.fixes_applied)} fixes:")
            for i, fix in enumerate(self.fixes_applied, 1):
                print(f"  {i}. {fix}")
        
        print("\n" + "="*60)
        print("NEXT STEPS:")
        print("="*60)
        
        if not self.issues or all("fixed" in fix.lower() for fix in self.fixes_applied):
            print("1. Run: python run_pipeline.py")
            print("2. Process emails: python -m vector_service.main process")
            print("3. Test search: python -m vector_service.main search 'test query'")
        else:
            print("1. Review the issues above")
            print("2. Run this script again after manual fixes")
            print("3. Ensure Legal BERT model downloads on first run")

def main():
    """Run the vector system debugger"""
    debugger = VectorDebugger()
    
    # Run diagnosis
    results = debugger.run_diagnosis()
    
    # Print summary
    debugger.print_summary()
    
    return 0 if not debugger.issues else 1

if __name__ == "__main__":
    sys.exit(main())

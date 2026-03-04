#!/usr/bin/env python3
"""
Diagnostic script to check if vector search is properly configured
Run this in your backend directory: python check_vector_setup.py
"""

import sys
from supabase import create_client

# Configuration (from your .env)
SUPABASE_URL = "https://grhttvtiarkxlwkoaqgj.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdyaHR0dnRpYXJreGx3a29hcWdqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTE5MjYzOCwiZXhwIjoyMDg0NzY4NjM4fQ.Ovla6FkO95nvoIE4MSdVpcHM9oWdj1_EdL7NE5P3_s4"

def check_setup():
    """Check if vector search is properly configured"""
    
    print("🔍 Checking Vector Search Setup...\n")
    
    try:
        client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Connected to Supabase\n")
        
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return False
    
    # Check 1: pgvector extension
    print("1️⃣  Checking pgvector extension...")
    try:
        result = client.rpc("match_embeddings", {
            "query_embedding": [0.0] * 384,
            "match_user_id": "test",
            "match_threshold": 0.7,
            "match_count": 1
        }).execute()
        print("   ✅ match_embeddings() RPC function EXISTS and is callable!\n")
        return True
        
    except Exception as e:
        error_msg = str(e).lower()
        if "unknown" in error_msg and "function" in error_msg:
            print("   ❌ match_embeddings() function does NOT exist")
            print(f"   Error: {e}\n")
            return False
        elif "permission" in error_msg:
            print("   ⚠️  Function exists but permission denied (RLS issue)")
            print(f"   Error: {e}\n")
            return True  # Function exists
        else:
            print(f"   ⚠️  Unexpected error: {e}\n")
            return False
    
if __name__ == "__main__":
    print("=" * 60)
    print("VECTOR SEARCH DIAGNOSTIC CHECK")
    print("=" * 60 + "\n")
    
    if check_setup():
        print("=" * 60)
        print("✅ SETUP COMPLETE - Vector search should work!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("❌ SETUP INCOMPLETE - You need to run SUPABASE_SETUP.sql")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Open: https://supabase.com/dashboard")
        print("2. Select your project")
        print("3. Go to SQL Editor → New Query")
        print("4. Copy content from: SUPABASE_SETUP.sql")
        print("5. Run the SQL commands")
        print("6. Re-run this diagnostic check")
        sys.exit(1)

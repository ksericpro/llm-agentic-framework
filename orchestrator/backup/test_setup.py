"""
Quick test script to verify the LangChain Agentic Pipeline setup
Run this after installing dependencies and setting up .env
"""

import sys
import os
from pathlib import Path


def check_dependencies():
    """Check if all required packages are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        "langchain",
        "langchain_core",
        "langchain_openai",
        "langgraph",
        "fastapi",
        "uvicorn",
        "pydantic",
        "dotenv",
        "openai",
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - NOT INSTALLED")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    print("\n✅ All dependencies installed!")
    return True


def check_env_file():
    """Check if .env file exists and has required keys"""
    print("\n🔍 Checking environment configuration...")
    
    env_path = Path(".env")
    
    if not env_path.exists():
        print("   ❌ .env file not found")
        print("   Create it from .env.example: cp .env.example .env")
        return False
    
    print("   ✅ .env file exists")
    
    # Load and check keys
    from dotenv import load_dotenv
    load_dotenv()
    
    required_keys = ["OPENAI_API_KEY"]
    optional_keys = ["TAVILY_API_KEY"]
    
    all_good = True
    for key in required_keys:
        value = os.getenv(key)
        if value and value != f"your-{key.lower().replace('_', '-')}-here":
            print(f"   ✅ {key} is set")
        else:
            print(f"   ❌ {key} is NOT set or using placeholder")
            all_good = False
    
    for key in optional_keys:
        value = os.getenv(key)
        if value and value != f"your-{key.lower().replace('_', '-')}-here":
            print(f"   ✅ {key} is set")
        else:
            print(f"   ⚠️  {key} is NOT set (optional, but web search won't work)")
    
    if not all_good:
        print("\n⚠️  Please set required API keys in .env file")
        return False
    
    print("\n✅ Environment configured!")
    return True


def test_imports():
    """Test if all custom modules can be imported"""
    print("\n🔍 Testing module imports...")
    
    modules = [
        "router_agent",
        "generator_agent",
        "intentplanning_agent",
        "critic_agent",
    ]
    
    all_good = True
    for module in modules:
        try:
            __import__(module)
            print(f"   ✅ {module}.py")
        except Exception as e:
            print(f"   ❌ {module}.py - Error: {str(e)[:50]}")
            all_good = False
    
    if not all_good:
        print("\n⚠️  Some modules have import errors")
        return False
    
    print("\n✅ All modules import successfully!")
    return True


def test_langchain_pipeline():
    """Test if the main pipeline can be initialized"""
    print("\n🔍 Testing LangChain pipeline initialization...")
    
    try:
        from langchain_openai import ChatOpenAI
        from langchain_pipeline import create_agent_graph
        
        # Try to create LLM (won't actually call API)
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY", "dummy-key")
        )
        print("   ✅ LLM initialized")
        
        # Try to create graph
        graph = create_agent_graph(llm)
        print("   ✅ LangGraph workflow created")
        
        print("\n✅ Pipeline initialization successful!")
        return True
    
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        print("\n⚠️  Pipeline initialization failed")
        return False


def test_api_import():
    """Test if the API can be imported"""
    print("\n🔍 Testing API import...")
    
    try:
        import api
        print("   ✅ api.py imports successfully")
        print("   ✅ FastAPI app created")
        
        print("\n✅ API ready to run!")
        print("\n   Start the API with:")
        print("   python api.py")
        print("   OR")
        print("   uvicorn api:app --reload --port 8000")
        
        return True
    
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        print("\n⚠️  API import failed")
        return False


def main():
    """Run all tests"""
    print("=" * 80)
    print("LANGCHAIN AGENTIC PIPELINE - SETUP VERIFICATION")
    print("=" * 80)
    
    results = []
    
    # Run all checks
    results.append(("Dependencies", check_dependencies()))
    results.append(("Environment", check_env_file()))
    results.append(("Module Imports", test_imports()))
    results.append(("Pipeline Init", test_langchain_pipeline()))
    results.append(("API Import", test_api_import()))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
        if not passed:
            all_passed = False
    
    print("=" * 80)
    
    if all_passed:
        print("\n🎉 ALL CHECKS PASSED! You're ready to go!")
        print("\nNext steps:")
        print("1. Start the API: python api.py")
        print("2. Test with client: python example_client.py")
        print("3. View docs: http://localhost:8000/docs")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Quick Setup Script for NYC Quick Hits
Checks dependencies and gets you running quickly
"""

import sys
import subprocess
import os

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required. Current version:", sys.version)
        return False
    print(f"✅ Python version: {sys.version}")
    return True

def check_dependencies():
    """Check and install required dependencies."""
    required_packages = [
        'pydantic',
        'requests', 
        'beautifulsoup4',
        'aiohttp',
        'asyncio-throttle'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} - installed")
        except ImportError:
            print(f"❌ {package} - missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n🔧 Installing missing packages: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("✅ Dependencies installed successfully!")
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies. Try manually:")
            print(f"pip install {' '.join(missing_packages)}")
            return False
    else:
        print("✅ All dependencies are installed!")
    
    return True

def check_environment():
    """Check environment variables."""
    required_vars = ['GOOGLE_API_KEY', 'GOOGLE_CSE_ID']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ {var} - not set")
            missing_vars.append(var)
        else:
            print(f"✅ {var} - set")
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("Create a .env file with:")
        for var in missing_vars:
            print(f"   {var}=your_value_here")
        return False
    
    return True

def run_quick_test():
    """Run a quick test to verify everything works."""
    try:
        print("\n🧪 Running quick test...")
        
        # Test basic imports
        from models import Lead
        print("✅ Models imported successfully")
        
        from lead_finder import LeadFinder
        print("✅ LeadFinder imported successfully")
        
        from google_cse import QueryManager
        print("✅ QueryManager imported successfully")
        
        print("✅ All imports successful! System is ready.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 NYC Quick Hits - Quick Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Check environment
    if not check_environment():
        return False
    
    # Run quick test
    if not run_quick_test():
        return False
    
    print("\n🎉 Setup complete! You can now run:")
    print("python3 search_scripts/nyc_quick_hits.py")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Setup failed. Please fix the issues above.")
        sys.exit(1) 
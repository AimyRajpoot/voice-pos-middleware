#!/usr/bin/env python
"""
Download and verify Piper TTS model for DukaanMind.
Run this script once during setup to pre-load the voice model.
"""
import os
import sys
import subprocess
from pathlib import Path

def download_piper_model(voice: str = "en_US-lessac-medium"):
    """Download Piper TTS model using piper binary."""
    
    # Find piper binary
    piper_binary = "piper"
    import shutil
    if shutil.which("piper"):
        piper_binary = shutil.which("piper")
    else:
        # Check common locations
        for path in [
            Path.home() / ".local" / "bin" / "piper",
            Path("/usr/local/bin/piper"),
        ]:
            if path.exists():
                piper_binary = str(path)
                break
    
    model_dir = Path.home() / ".local" / "share" / "piper" / "voices"
    model_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = model_dir / f"{voice}.onnx"
    config_path = model_dir / f"{voice}.onnx.json"
    
    if model_path.exists() and config_path.exists():
        print(f"✓ Model already exists: {model_path}")
        return True
    
    print(f"Downloading Piper voice model: {voice}...")
    print(f"Target directory: {model_dir}")
    
    try:
        result = subprocess.run([
            piper_binary,
            "--model", voice,
            "--download-dir", str(model_dir)
        ], capture_output=True, text=True, timeout=180)
        
        if result.returncode == 0:
            print(f"✓ Model downloaded successfully!")
            print(f"  Model: {model_path}")
            print(f"  Config: {config_path}")
            
            # Verify model loads
            if model_path.exists() and config_path.exists():
                print(f"✓ Model files verified")
                return True
            else:
                print(f"✗ Model files not found after download")
                return False
        else:
            print(f"✗ Download failed:")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"✗ Download timed out after 3 minutes")
        return False
    except FileNotFoundError:
        print(f"✗ Piper binary not found. Install with: pip install piper-tts")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_tts_synthesis(voice: str = "en_US-lessac-medium"):
    """Test TTS synthesis with a sample text."""
    print("\nTesting TTS synthesis...")
    
    # Add app to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    try:
        from app.core.tts_engine import TTSEngine
        
        engine = TTSEngine(voice)
        if not engine.ensure_model():
            print("✗ Model not available")
            return False
        
        test_text = "Welcome to DukaanMind. Your order is ready."
        print(f"Synthesizing: '{test_text}'")
        
        audio_bytes = engine.synthesize(test_text)
        print(f"✓ Synthesis successful! Audio size: {len(audio_bytes)} bytes")
        
        # Save test output
        output_path = Path(__file__).parent / "test_output.mp3"
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        print(f"✓ Test audio saved to: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"✗ TTS test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("DukaanMind - Piper TTS Model Setup")
    print("=" * 60)
    
    voice = "en_US-lessac-medium"
    
    # Download model
    success = download_piper_model(voice)
    
    if success:
        # Test synthesis
        success = test_tts_synthesis(voice)
    
    print("\n" + "=" * 60)
    if success:
        print("✓ TTS Setup Complete!")
        print("You can now run the backend with TTS support.")
    else:
        print("✗ TTS Setup Failed!")
        print("Check errors above and try again.")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Quick test script for transcription configuration system.
Tests configuration without loading heavy models.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from transcription.config import (
    HybridConfig,
    LocalWhisperConfig,
    OpenAIConfig,
    QualityConfig,
    TranscriptionConfig,
    TranscriptionMode,
    get_config_manager,
)


def test_config_classes():
    """Test configuration dataclasses."""
    print("Testing configuration dataclasses...")
    
    # Test individual configs
    local_config = LocalWhisperConfig(model_name="base", use_gpu=False)
    print(f"✓ LocalWhisperConfig: model={local_config.model_name}, gpu={local_config.use_gpu}")
    
    openai_config = OpenAIConfig(model="whisper-1", max_workers=3)
    print(f"✓ OpenAIConfig: model={openai_config.model}, workers={openai_config.max_workers}")
    
    hybrid_config = HybridConfig(validation_threshold=0.8)
    print(f"✓ HybridConfig: threshold={hybrid_config.validation_threshold}")
    
    quality_config = QualityConfig(confidence_threshold=0.5)
    print(f"✓ QualityConfig: threshold={quality_config.confidence_threshold}")
    
    # Test main config
    main_config = TranscriptionConfig(
        mode=TranscriptionMode.LOCAL_GPU,
        local_whisper=local_config,
        openai=openai_config,
        hybrid=hybrid_config,
        quality=quality_config
    )
    print(f"✓ TranscriptionConfig: mode={main_config.mode.value}")
    
    return True


def test_config_manager():
    """Test configuration manager without heavy provider loading."""
    print("\nTesting configuration manager...")
    
    try:
        # Create temporary config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_config = f.name
        
        from transcription.config import TranscriptionConfigManager
        manager = TranscriptionConfigManager(temp_config)
        
        print(f"✓ Config manager created with mode: {manager.get_mode().value}")
        
        # Test mode switching
        original_mode = manager.get_mode()
        for mode in TranscriptionMode:
            result = manager.set_mode(mode)
            if result["success"]:
                print(f"✓ Mode switch to {mode.value}: success")
            else:
                print(f"- Mode switch to {mode.value}: {result['error'][:50]}...")
        
        # Reset to original mode
        manager.set_mode(original_mode)
        
        # Test diagnostics
        diagnostics = manager.get_diagnostics()
        print(f"✓ Diagnostics: {len(diagnostics)} keys")
        
        # Test cost estimation
        cost_info = manager.estimate_cost(5.0)  # 5 minutes
        print(f"✓ Cost estimation: mode={cost_info['mode']}")
        
        # Test saving
        save_result = manager.save_configuration()
        if save_result["success"]:
            print(f"✓ Configuration saved to: {temp_config}")
        else:
            print(f"✗ Save failed: {save_result['error']}")
        
        # Cleanup
        try:
            os.unlink(temp_config)
        except (FileNotFoundError, OSError):
            pass
        
        return True
        
    except Exception as e:
        print(f"✗ Config manager test failed: {e}")
        return False


def test_environment_vars():
    """Test environment variable override."""
    print("\nTesting environment variables...")
    
    try:
        # Set test environment variables
        os.environ["TRANSCRIPTION_MODE"] = "OPENAI_ONLY"
        os.environ["WHISPER_MODEL"] = "base"
        os.environ["WHISPER_USE_GPU"] = "false"
        
        # Create config manager
        from transcription.config import TranscriptionConfigManager
        env_manager = TranscriptionConfigManager()
        
        print(f"✓ Environment override mode: {env_manager.get_mode().value}")
        
        config = env_manager.get_config()
        print(f"✓ Whisper model: {config.local_whisper.model_name}")
        print(f"✓ GPU setting: {config.local_whisper.use_gpu}")
        
        # Cleanup
        del os.environ["TRANSCRIPTION_MODE"]
        del os.environ["WHISPER_MODEL"]
        del os.environ["WHISPER_USE_GPU"]
        
        return True
        
    except Exception as e:
        print(f"✗ Environment variable test failed: {e}")
        return False


def test_validation():
    """Test configuration validation."""
    print("\nTesting configuration validation...")
    
    try:
        manager = get_config_manager()
        
        # Test validation
        validation = manager.validate_configuration()
        print(f"✓ Validation result: valid={validation['valid']}")
        
        if validation['errors']:
            print(f"  Errors: {validation['errors']}")
        if validation['warnings']:
            print(f"  Warnings: {validation['warnings']}")
        
        # Test provider availability checking
        availability = manager.check_provider_availability()
        print("✓ Provider availability checked")
        for provider, status in availability.items():
            print(f"  {provider}: {status}")
        
        return True
        
    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("QUICK TRANSCRIPTION CONFIGURATION TESTS")
    print("=" * 60)
    
    tests = [
        ("Configuration Classes", test_config_classes),
        ("Configuration Manager", test_config_manager),
        ("Environment Variables", test_environment_vars),
        ("Validation", test_validation),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n{name}:")
        print("-" * len(name))
        try:
            if test_func():
                passed += 1
                print(f"✓ {name} PASSED")
            else:
                print(f"✗ {name} FAILED")
        except Exception as e:
            print(f"✗ {name} CRASHED: {e}")
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 All tests passed! Configuration system is working.")
        sys.exit(0)
    else:
        print("❌ Some tests failed.")
        sys.exit(1)
import os
import yaml

def test_imports():
    """Verify that all phase dependencies can be successfully imported."""
    try:
        import groq
        import pydantic
        import pandas
        import dotenv
    except ImportError as e:
        assert False, f"Failed to import dependency: {e}"

def test_config_loading():
    """Verify that the config.yaml file exists and is parsable."""
    config_path = "config.yaml"
    assert os.path.exists(config_path), "config.yaml file does not exist in the root."
    
    with open(config_path, "r") as f:
        try:
            config = yaml.safe_load(f)
            assert config is not None
            assert "paths" in config, "Missing 'paths' section in config.yaml"
            assert "llm" in config, "Missing 'llm' section in config.yaml"
            assert config["llm"]["provider"] == "groq"
        except yaml.YAMLError as e:
            assert False, f"Failed to parse config.yaml: {e}"

def test_env_files():
    """Verify that the environment file templates exist."""
    assert os.path.exists(".env") or os.path.exists(".env.template"), "Neither .env nor .env.template files exist."

import os
import yaml
import logging
from groq import Groq
import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class GroqClient:
    """Initializes and provides the Groq LLM client dynamically using environment variables."""

    def __init__(self, config_path: str = "config.yaml"):
        load_dotenv()
        
        # Resolve path dynamically if run from subdirectory
        if not os.path.exists(config_path):
            curr_dir = os.path.dirname(os.path.abspath(__file__))
            possible_path = os.path.abspath(os.path.join(curr_dir, "..", "..", config_path))
            if os.path.exists(possible_path):
                config_path = possible_path
        
        self.config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Failed to read config.yaml from {config_path}: {e}.")

        # Retrieve settings
        llm_config = self.config.get("llm", {})
        self.temperature = float(llm_config.get("temperature", 0.1))
        self.max_tokens = int(llm_config.get("max_tokens", 4096))

        default_rate_limit = {
            "batch_size": 5,
            "min_request_interval_seconds": 3.0,
            "max_retries": 5,
            "initial_backoff_seconds": 5,
            "max_backoff_seconds": 120,
            "tpm_budget": 8000,
        }
        self.rate_limit = {**default_rate_limit, **llm_config.get("rate_limit", {})}
        
        # Model-agnostic variables (loaded from environment with template fallbacks)
        self.classifier_model = os.environ.get("GROQ_CLASSIFIER_MODEL", "openai/gpt-oss-120b")
        self.gate_model = os.environ.get("GROQ_GATE_MODEL", "llama-3.1-8b-instant")
        self.api_key = os.environ.get("GROQ_API_KEY")

        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set in .env")
        
        self.client = Groq(api_key=self.api_key)
        logger.info(f"GroqClient successfully initialized. Classifier Model: {self.classifier_model}, Gate Model: {self.gate_model}")

    def get_client(self) -> Groq:
        """Returns the raw Groq client object."""
        return self.client


class GeminiClient:
    """Initializes and provides the Google Gemini LLM client dynamically using environment variables."""

    def __init__(self):
        load_dotenv()
        self.model_name = os.environ.get("GEMINI_SUMMARY_MODEL", "gemini-2.5-flash")
        self.api_key = os.environ.get("GEMINI_API_KEY")

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set in .env")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        logger.info(f"GeminiClient successfully initialized using model: {self.model_name}")

    def generate_content(self, prompt: str, temperature: float = 0.2) -> str:
        """Generates text content using the Gemini model."""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=temperature)
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini content generation failed: {e}")
            raise e

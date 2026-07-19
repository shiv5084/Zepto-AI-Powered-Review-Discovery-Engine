import os
import sys
import argparse
import logging
import yaml
import pandas as pd
import json
from dotenv import load_dotenv

# Add project root to python path to resolve src imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingestion.ingestor import IngestionManager
from src.processing.llm_client import GroqClient, GeminiClient
from src.processing.review_processor import ReviewProcessor
from src.analysis.theme_discoverer import ThemeDiscoverer
from src.reporting.pulse_generator import PulseGenerator
from src.reporting.json_exporter import JSONExporter, pad_analysis_results
from src.db.neon_client import NeonClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("PRDE-Orchestrator")

def load_config(config_path: str = "config.yaml") -> dict:
    """Loads configuration options from config.yaml."""
    if not os.path.exists(config_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt_path = os.path.join(script_dir, "..", config_path)
        if os.path.exists(alt_path):
            config_path = alt_path

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    logger.warning(f"Config file not found at '{config_path}'. Using defaults.")
    return {}

def run_phase1(config: dict, num_records: int = None) -> pd.DataFrame:
    """Executes Phase 1: Data Ingestion & PII Scrubbing."""
    logger.info("Executing Phase 1: Ingestion & PII Scrubbing...")
    paths = config.get("paths", {})
    raw_dir = paths.get("raw_data_dir", "data/raw")
    processed_dir = paths.get("processed_data_dir", "data/processed")
    
    # Ensure any existing output file is deleted first
    reviews_csv = os.path.join(processed_dir, "reviews.csv")
    if os.path.exists(reviews_csv):
        try:
            os.remove(reviews_csv)
            logger.info(f"Deleted existing Phase 1 output file: {reviews_csv}")
        except Exception as e:
            logger.warning(f"Could not delete existing Phase 1 output: {e}")
            
    manager = IngestionManager(raw_dir=raw_dir, processed_dir=processed_dir)
    df = manager.run(num_records=num_records)
    manager.close()
    logger.info(f"Phase 1 completed successfully. Ingested & processed {len(df)} records.")
    return df

def run_phase2(config: dict, num_records: int = None) -> pd.DataFrame:
    """Executes Phase 2: Theme Extraction & Metric Parsing (LLM)."""
    logger.info("Executing Phase 2: Theme Extraction & Metric Parsing...")
    paths = config.get("paths", {})
    processed_dir = paths.get("processed_data_dir", "data/processed")
    reviews_csv = os.path.join(processed_dir, "reviews.csv")
    
    if not os.path.exists(reviews_csv):
        logger.error(f"Processed reviews CSV missing at '{reviews_csv}'. Run Phase 1 first.")
        raise FileNotFoundError("Missing processed/reviews.csv")
        
    annotated_json = os.path.join(processed_dir, "annotated_reviews.json")
    if os.path.exists(annotated_json):
        try:
            os.remove(annotated_json)
            logger.info(f"Deleted existing Phase 2 output file: {annotated_json}")
        except Exception as e:
            logger.warning(f"Could not delete existing Phase 2 output: {e}")

    df = pd.read_csv(reviews_csv)
    if df.empty:
        logger.error("No reviews found to process in reviews.csv.")
        return df

    # Initialize clients
    groq_client = GroqClient()
    neon_client = NeonClient()
    
    processor = ReviewProcessor(groq_client)

    opt_config = config.get("optimization", {})
    opt_enabled = opt_config.get("enabled", True)

    if opt_enabled:
        sampling_cfg = opt_config.get("sampling", {})
        sample_size = num_records or sampling_cfg.get("sample_size", 500)
        min_floor_sources = sampling_cfg.get("min_floor_sources", ["reddit", "product_reviews", "twitter"])
        
        gate_cfg = opt_config.get("gate", {})
        gate_enabled = gate_cfg.get("enabled", True)
        gate_batch_size = gate_cfg.get("batch_size", 10)
        
        logger.info(
            f"Running OPTIMIZED Phase 2 pipeline (sample_size={sample_size}, "
            f"gate_enabled={gate_enabled})..."
        )
        annotated_df, coverage = processor.process_reviews_optimized(
            df,
            sample_size=sample_size,
            min_floor_sources=min_floor_sources,
            gate_enabled=gate_enabled,
            gate_batch_size=gate_batch_size,
            neon_client=neon_client
        )
        logger.info("Optimized Phase 2 complete.")
    else:
        limit = num_records or min(300, len(df))
        logger.info(f"Running UNOPTIMIZED Phase 2 pipeline (limit={limit})...")
        annotated_df = processor.process_reviews(df, num_records=limit)
        
    neon_client.close()
    logger.info(f"Phase 2 completed successfully. Annotated {len(annotated_df)} records.")
    return annotated_df

def run_phase3(config: dict) -> dict:
    """Executes Phase 3: Analytical Theme Aggregation."""
    logger.info("Executing Phase 3: Analytical Theme Discovery & Aggregation...")
    paths = config.get("paths", {})
    processed_dir = paths.get("processed_data_dir", "data/processed")
    annotated_json = os.path.join(processed_dir, "annotated_reviews.json")
    output_path = os.path.join(processed_dir, "analysis_results.json")
    
    if not os.path.exists(annotated_json):
        logger.error(f"Annotated JSON missing at '{annotated_json}'. Run Phase 2 first.")
        raise FileNotFoundError("Missing annotated_reviews.json")
        
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
            logger.info(f"Deleted existing Phase 3 output file: {output_path}")
        except Exception as e:
            logger.warning(f"Could not delete existing Phase 3 output: {e}")

    # Pass GeminiClient to ThemeDiscoverer to support Q6 frustrations root causes LLM queries
    gemini_client = GeminiClient()
    discoverer = ThemeDiscoverer(gemini_client)

    results = discoverer.perform_full_analysis(annotated_json, output_path)
    logger.info("Phase 3 completed successfully. Local aggregation results saved.")
    return results

def run_phase4(config: dict) -> str:
    """Executes Phase 4: Pulse Note Generation & JSON Export."""
    logger.info("Executing Phase 4: Pulse Note Generation & JSON Export...")
    paths = config.get("paths", {})
    processed_dir = paths.get("processed_data_dir", "data/processed")
    analysis_json = os.path.join(processed_dir, "analysis_results.json")
    
    pulse_note_file = paths.get("pulse_note_file", "data/weekly_pulse_note.md")
    dashboard_json_file = paths.get("dashboard_json_file", "data/dashboard_data.json")
    
    if not os.path.exists(analysis_json):
        logger.error(f"Analysis results JSON missing at '{analysis_json}'. Run Phase 3 first.")
        raise FileNotFoundError("Missing analysis_results.json")
        
    for path_to_del in [pulse_note_file, dashboard_json_file]:
        if os.path.exists(path_to_del):
            try:
                os.remove(path_to_del)
                logger.info(f"Deleted existing Phase 4 output file: {path_to_del}")
            except Exception as e:
                logger.warning(f"Could not delete existing Phase 4 output '{path_to_del}': {e}")

    with open(analysis_json, "r", encoding="utf-8") as f:
        analysis_results = json.load(f)

    # Pad each section to exactly 3 items
    padded_results = pad_analysis_results(analysis_results)

    groq_client = GroqClient()
    gemini_client = GeminiClient()
    
    generator = PulseGenerator(groq_client, gemini_client)
    exporter = JSONExporter(config)

    # Pulse note & opportunities generation
    pulse_note, opps = generator.generate_weekly_pulse_note(padded_results)

    # Dashboard JSON export
    exporter.export_dashboard_json(padded_results, opps, pulse_note, dashboard_json_file)

    logger.info("Phase 4 completed successfully. Executive Pulse note and JSON dashboard metrics saved.")
    return pulse_note

def main():
    # Load dotenv credentials relative to the root directory
    dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    load_dotenv(dotenv_path=dotenv_path)
    
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Zepto AI-Powered Cross-Category Discovery Engine (PRDE)")
    parser.add_argument(
        "--phase",
        type=str,
        default="all",
        choices=["1", "2", "3", "4", "all"],
        help="Specify which execution phase to run (default: all)"
    )
    parser.add_argument(
        "--num-records",
        type=int,
        default=None,
        help="Limit the number of raw records ingested (Phase 1) or annotated (Phase 2)"
    )
    
    args = parser.parse_args()
    config = load_config()

    try:
        if args.phase == "1":
            run_phase1(config, args.num_records)
        elif args.phase == "2":
            run_phase2(config, args.num_records)
        elif args.phase == "3":
            run_phase3(config)
        elif args.phase == "4":
            run_phase4(config)
        else:
            logger.info("Starting complete end-to-end Zepto PRDE pipeline execution...")
            run_phase1(config, args.num_records)
            run_phase2(config, args.num_records)
            run_phase3(config)
            run_phase4(config)
            logger.info("E2E pipeline execution completed successfully.")
            
    except Exception as e:
        logger.error(f"Pipeline execution encountered an error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

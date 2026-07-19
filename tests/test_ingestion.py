import os
import pandas as pd
import pytest
from unittest.mock import patch
from src.ingestion.pii_scrubber import PIIScrubber
from src.ingestion.ingestor import IngestionManager

def test_pii_scrubber_regex():
    scrubber = PIIScrubber()
    
    # Test Email Scrubbing
    assert scrubber.scrub("test email: john.doe@zepto.com") == "test email: [EMAIL]"
    
    # Test IP Address Scrubbing
    assert scrubber.scrub("my IP is 192.168.1.1") == "my IP is [IP_ADDRESS]"
    
    # Test Phone Number Scrubbing
    assert scrubber.scrub("call 555-123-4567 today") == "call [PHONE_NUMBER] today"
    
    # Test Reddit Handle Scrubbing
    assert scrubber.scrub("post by u/zepto_fan") == "post by [USER_HANDLE]"
    assert scrubber.scrub("check /u/quick_delivery") == "check [USER_HANDLE]"
    
    # Test Twitter Handle Scrubbing
    assert scrubber.scrub("ping @zepto_help on twitter") == "ping [USER_HANDLE] on twitter"

def test_pii_scrubber_presidio():
    scrubber = PIIScrubber()
    # If Presidio is active, test name scrubbing
    if scrubber.presidio_available:
        text = "Hello, my name is John Smith and my email is john@smith.org"
        scrubbed = scrubber.scrub(text)
        assert "[REDACTED_NAME]" in scrubbed
        assert "[EMAIL]" in scrubbed
    else:
        # If presidio falls back, regex must still mask email
        assert scrubber.scrub("john@smith.org") == "[EMAIL]"

@patch("src.ingestion.scrapers.PublicReviewScraper.scrape_google_play")
@patch("src.ingestion.scrapers.PublicReviewScraper.scrape_app_store")
@patch("src.ingestion.scrapers.PublicReviewScraper.scrape_reddit")
@patch("src.ingestion.scrapers.PublicReviewScraper.scrape_twitter")
@patch("src.ingestion.scrapers.PublicReviewScraper.scrape_trustpilot")
@patch("src.ingestion.ingestor.NeonClient")
def test_ingestion_manager_normalization(mock_neon, mock_tp, mock_tw, mock_rd, mock_as, mock_gp, tmp_path):
    # Setup mock returns
    mock_gp.return_value = pd.DataFrame([{
        "source": "google_play",
        "date": "2026-07-19",
        "title": "Great App",
        "text": "This is a great app for groceries.",
        "rating": 5,
        "engagement": 0
    }])
    mock_as.return_value = pd.DataFrame([{
        "source": "app_store",
        "date": "2026-07-19",
        "title": "Nice",
        "text": "Very convenient quick commerce.",
        "rating": 4,
        "engagement": 0
    }])
    mock_rd.return_value = pd.DataFrame([])
    mock_tw.return_value = pd.DataFrame([])
    mock_tp.return_value = pd.DataFrame([])

    # Disable NeonDB connection for this unit test
    mock_neon.return_value.enabled = False

    raw_dir = os.path.join(tmp_path, "raw")
    processed_dir = os.path.join(tmp_path, "processed")
    
    manager = IngestionManager(raw_dir=raw_dir, processed_dir=processed_dir)
    df = manager.run(num_records=10)
    
    # Assert output shape is within bounds
    assert not df.empty
    assert len(df) > 0
    
    # Assert columns match schema
    expected_cols = {"db_id", "source", "date", "title", "text", "rating", "engagement"}
    assert set(df.columns) == expected_cols
    
    # Verify raw and processed file creations
    assert os.path.exists(os.path.join(raw_dir, "raw_reviews.csv"))
    assert os.path.exists(os.path.join(processed_dir, "reviews.csv"))

@patch("src.ingestion.scrapers.PublicReviewScraper.scrape_google_play")
@patch("src.ingestion.scrapers.PublicReviewScraper.scrape_app_store")
@patch("src.ingestion.scrapers.PublicReviewScraper.scrape_reddit")
@patch("src.ingestion.scrapers.PublicReviewScraper.scrape_twitter")
@patch("src.ingestion.scrapers.PublicReviewScraper.scrape_trustpilot")
@patch("src.ingestion.ingestor.NeonClient")
def test_normalization_formats(mock_neon, mock_tp, mock_tw, mock_rd, mock_as, mock_gp, tmp_path):
    mock_gp.return_value = pd.DataFrame([{
        "source": "google_play",
        "date": "2026-07-19",
        "title": "Great App",
        "text": "This is a great app for groceries.",
        "rating": 5,
        "engagement": 0
    }])
    mock_as.return_value = pd.DataFrame([])
    mock_rd.return_value = pd.DataFrame([])
    mock_tw.return_value = pd.DataFrame([])
    mock_tp.return_value = pd.DataFrame([])

    # Disable NeonDB connection for this unit test
    mock_neon.return_value.enabled = False

    raw_dir = os.path.join(tmp_path, "raw")
    processed_dir = os.path.join(tmp_path, "processed")
    
    manager = IngestionManager(raw_dir=raw_dir, processed_dir=processed_dir)
    df = manager.run(num_records=5)
    
    assert len(df) > 0
    for _, row in df.iterrows():
        assert isinstance(row["source"], str)
        assert len(row["date"]) == 10
        assert row["date"][4] == "-"
        assert row["date"][7] == "-"
        assert pd.isna(row["rating"]) or isinstance(row["rating"], (int, float))
        assert pd.isna(row["engagement"]) or isinstance(row["engagement"], (int, float))

def test_data_cleaning_logic():
    from src.ingestion.ingestor import strip_emojis, clean_sentence_length, is_spam
    
    # 1. Test Emoji Removal
    assert strip_emojis("Love this app! 😊🎸🔥") == "Love this app! "
    
    # 2. Test Sentence Length check (removes sentences with less than 5 words)
    text_with_short_sentences = "This app is really good. But repeating loop. I like the category discovery feature."
    cleaned = clean_sentence_length(text_with_short_sentences)
    assert "This app is really good." in cleaned
    assert "I like the category discovery feature." in cleaned
    assert "But repeating loop." not in cleaned
    
    # 3. Test Spam Check
    assert is_spam("Buy now click this link to win money!") is True
    assert is_spam("aaaaaa and other repeating characters") is True
    assert is_spam("normal review with a lot of details about grocery delivery speeds") is False

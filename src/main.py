#!/usr/bin/env python3
"""
RFP Web Crawler - Main Entry Point

This module orchestrates the complete pipeline:
- Load existing tracker CSV from GCS
- Crawl websites and collect RFPs
- Download files, extract text, infer details and corrigendum
- Summarise and tag relevant RMs
- Update and overwrite the tracker CSV to GCS
"""

import os
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import requests
import pandas as pd

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.settings import *
from src.parsers import get_parser_for_website
from src.utils.helpers import generate_rfp_id
from src.llm_utils.text_extraction import text_extraction
from src.llm_utils.summarisation import summarise_text_with_gemini
from src.llm_utils.rm_tagger import get_relevant_rms
from src.llm_utils.llm_detail_extraction import extarct_details


def _ensure_dirs():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)


def _yesterday_date():
    return (datetime.utcnow() - timedelta(days=1)).date()


def _load_tracker_df(uri: Optional[str]) -> pd.DataFrame:
    if not uri:
        return pd.DataFrame()
    try:
        return pd.read_csv(uri, storage_options={"token": "google_default"})
    except Exception as e:
        print(f"Warning: could not load tracker CSV from {uri}: {e}")
        return pd.DataFrame()


def _save_tracker_df(df: pd.DataFrame, uri: Optional[str]) -> None:
    if not uri or df is None:
        return
    try:
        df.to_csv(uri, index=False, storage_options={"token": "google_default"})
        print(f"Tracker CSV saved to {uri}")
    except Exception as e:
        print(f"Warning: could not save tracker CSV to {uri}: {e}")


def _download_file(url: str, title: str, index: int) -> Optional[str]:
    try:
        if not url:
            return None
        safe_title = (title or 'rfp').replace('/', '_').replace(' ', '_')[:50]
        ext = os.path.splitext(url)[1] or '.bin'
        filename = f"{safe_title}_{index}{ext}"
        local_path = os.path.join(DOWNLOAD_DIR, filename)
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(resp.content)
            return local_path
        print(f"Failed to download {url}: {resp.status_code}")
        return None
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None


def main(start_date: Optional[str] = None, end_date: Optional[str] = None):
    _ensure_dirs()

    # Dates default to yesterday (inclusive window)
    yday = _yesterday_date()
    start_dt = datetime.fromisoformat(start_date).date() if start_date else yday
    end_dt = datetime.fromisoformat(end_date).date() if end_date else yday

    # Load tracker CSV
    tracker_uri = GCS_RFP_TRACKER_CSV_URI
    tracker_df = _load_tracker_df(tracker_uri)

    all_rfps: List[Dict[str, Any]] = []
    print(f"Starting crawl for {len(WEBSITES)} websites | window: {start_dt} to {end_dt}")

    # Crawl and parse
    for website in WEBSITES:
        try:
            parser = get_parser_for_website(website)
        except ValueError as e:
            print(f"Parser error for {website.get('name')}: {e}")
            continue

        try:
            rfps = parser.parse(start_date=start_dt, end_date=end_dt)
            for r in rfps:
                r['website_name'] = website['name']
                r['website_url'] = website['url']
                r['rfp_id'] = generate_rfp_id(r)
                # default start_date
                if not r.get('start_date'):
                    r['start_date'] = str(start_dt)
            print(f"Crawled {website['name']}: {len(rfps)} RFPs in window (parser filtered)")
            all_rfps.extend(rfps)
        except Exception as e:
            print(f"Error parsing {website.get('name')}: {e}")
            continue

    # Process pipeline per RFP
    if tracker_df.empty:
        tracker_df = pd.DataFrame(columns=[
            CSV_COL_INTERNAL_ID,
            CSV_COL_EXTERNAL_ID,
            CSV_COL_ORIGINAL_FILE_PATH,
            CSV_COL_RELEVANT_RMS,
        ])

    for rfp in all_rfps:
        title = rfp.get('title') or 'rfp'
        file_urls = rfp.get('file_urls') or []

        # Download attached files
        local_files: List[str] = []
        for idx, url in enumerate(file_urls):
            p = _download_file(url, title, idx)
            if p:
                local_files.append(p)

        # Extract text
        texts: List[str] = []
        for p in local_files:
            t = text_extraction(p)
            if t:
                texts.append(t)
        combined_text = "\n\n".join([t for t in texts if t])

        # Extract details and infer corrigendum
        extracted_external_id = None
        is_corrigendum = rfp.get('corregendum')
        try:
            details = extarct_details(combined_text)  # expected dict with keys incl. rfp_external_id
            if isinstance(details, dict):
                extracted_external_id = details.get('rfp_external_id')
        except TypeError:
            details = None

        if is_corrigendum in (None, "", False):
            if extracted_external_id and not tracker_df.empty and CSV_COL_EXTERNAL_ID in tracker_df.columns:
                match = tracker_df[tracker_df[CSV_COL_EXTERNAL_ID] == extracted_external_id]
                is_corrigendum = not match.empty
            else:
                is_corrigendum = False
        rfp['corregendum'] = bool(is_corrigendum)

        # If corrigendum, include original file text
        original_text = ""
        if rfp['corregendum'] and extracted_external_id and not tracker_df.empty:
            match = tracker_df[tracker_df[CSV_COL_EXTERNAL_ID] == extracted_external_id]
            if not match.empty and CSV_COL_ORIGINAL_FILE_PATH in match.columns:
                orig_path_or_url = match.iloc[0].get(CSV_COL_ORIGINAL_FILE_PATH)
                if isinstance(orig_path_or_url, str) and orig_path_or_url:
                    if os.path.exists(orig_path_or_url):
                        original_text = text_extraction(orig_path_or_url) or ""
                    elif orig_path_or_url.startswith('http'):
                        tmp = _download_file(orig_path_or_url, title + "_orig", 0)
                        if tmp:
                            original_text = text_extraction(tmp) or ""

        summary_input_text = (original_text + ("\n\n" if (original_text and combined_text) else "") + combined_text).strip()
        summary_text = summarise_text_with_gemini(summary_input_text) if summary_input_text else ""

        # Tag relevant RMs
        try:
            relevant_rms = get_relevant_rms(summary_text) or []
        except Exception:
            relevant_rms = []

        # Update tracker by external id
        ext_id_for_tracker = extracted_external_id or rfp.get('external_id')
        if ext_id_for_tracker:
            if tracker_df.empty:
                tracker_df = pd.DataFrame(columns=[
                    CSV_COL_INTERNAL_ID,
                    CSV_COL_EXTERNAL_ID,
                    CSV_COL_ORIGINAL_FILE_PATH,
                    CSV_COL_RELEVANT_RMS,
                ])
            mask = tracker_df[CSV_COL_EXTERNAL_ID] == ext_id_for_tracker if CSV_COL_EXTERNAL_ID in tracker_df.columns else pd.Series([False] * len(tracker_df))
            row = {
                CSV_COL_EXTERNAL_ID: ext_id_for_tracker,
                CSV_COL_RELEVANT_RMS: ",".join(relevant_rms) if relevant_rms else "",
            }
            if local_files and (CSV_COL_ORIGINAL_FILE_PATH in tracker_df.columns):
                row[CSV_COL_ORIGINAL_FILE_PATH] = local_files[0]
            if mask.any():
                for k, v in row.items():
                    tracker_df.loc[mask, k] = v
            else:
                tracker_df = pd.concat([tracker_df, pd.DataFrame([row])], ignore_index=True)

    # Save tracker CSV back to GCS
    _save_tracker_df(tracker_df, tracker_uri)

    print("Pipeline finished")


if __name__ == "__main__":
    main()

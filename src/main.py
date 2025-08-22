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
from src.crawler.crawl_manager import get_crawler_for_website
from src.utils.helpers import *
from src.llm_utils.text_extraction import text_extraction
from src.llm_utils.summarisation import Summariser
from src.llm_utils.rm_tagger import get_relevant_rms
from src.llm_utils.llm_detail_extraction import extract_rfp_details


def _ensure_dirs():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)


def _yesterday_date():
    return (datetime.utcnow() - timedelta(days=1)).date()


def main():
    _ensure_dirs()
    start_date = CRAWL_START_DATE
    end_date = CRAWL_END_DATE

    # Dates default to yesterday (inclusive window)
    yday = _yesterday_date()
    start_dt = datetime.fromisoformat(start_date).date() if start_date else yday
    end_dt = datetime.fromisoformat(end_date).date() if end_date else yday

    # Load tracker CSV
    tracker_df = load_tracker_df()

    all_rfps: List[Dict[str, Any]] = []
    print(f"Starting crawl for {len(WEBSITES)} websites | window: {start_dt} to {end_dt}")

    # Crawl and parse
    for website in WEBSITES:
        try:
            parser = get_crawler_for_website(website['type'])
        except ValueError as e:
            print(f"Parser error for {website.get('name')}: {e}")
            continue

        try:
            rfps = parser(website['search_key_words'], start_date=start_dt, end_date=end_dt)
            for r in rfps:
                r['website_name'] = website['name']
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
            CSV_COL_CAPABILITY_COMPARISON,
            CSV_COL_DOCUMENT_COMPARISON,
            CSV_COL_DUE_DATES,
            CSV_COL_CORRIGENDUM,
            CSV_COL_SUMMARY_LINK,
            CSV_COL_TITLE,
        ])

    for rfp in all_rfps:
        title = rfp.get('title') or 'rfp'
        file_url = rfp.get('document_url') or ""

        # Download attached files
        local_file = download_file_from_url(file_url, title, DOWNLOAD_DIR) or None
        rfp['local_file'] = local_file
        file_name = os.path.basename(local_file)

        # Extract text
        if local_file:
            text = text_extraction(local_file)
            rfp['text'] = text

        # Extract details and infer corrigendum
        extracted_external_id = None

        # Corrigendum handling based on tracker by title
        corrigendum_num = rfp.get('corregendum')
        if corrigendum_num and isinstance(tracker_df, pd.DataFrame) and not tracker_df.empty:
            try:
                current_num = int(str(corrigendum_num).strip())
            except Exception:
                current_num = None

            if current_num:
                match = tracker_df[tracker_df[CSV_COL_TITLE] == title]
                if not match.empty:
                    prev_raw = match.iloc[0].get(CSV_COL_CORRIGENDUM)
                    try:
                        prev_num = int(str(prev_raw).strip()) if prev_raw is not None else None
                    except Exception:
                        prev_num = None

                    if prev_num is not None:
                        if prev_num == current_num:
                            # no change
                            print(" Skipping as it seems to be an SBI RFP which is not a corrigendum")
                            continue
                        elif prev_num < current_num:
                            # newer corrigendum detected
                            rfp['opening_date'] = str(_yesterday_date())
                            rfp['is_corregendum'] = True
                            rfp['match_internal_id'] = match.iloc[0].get(CSV_COL_INTERNAL_ID)

        try:
            details = extract_rfp_details(text)  # expected dict with keys incl. rfp_external_id
            if isinstance(details, dict):
                extracted_external_id = details.get('rfp_id')
                due_dates = details.get('events')
        except TypeError:
            details = None

        # If SBI Type Corregendum
        if extracted_external_id and not tracker_df.empty:
            match = tracker_df[tracker_df[CSV_COL_EXTERNAL_ID] == extracted_external_id]
            rfp['is_corrigendum'] = not match.empty
            rfp['match_internal_id'] = match.iloc[0].get(CSV_COL_INTERNAL_ID)

        # If corrigendum, compose text from original + specific corrigendum files + current
        if rfp.get('is_corrigendum') and ('corrigendum' not in rfp.keys()):
            original_text = ""
            corrigenda_texts: List[str] = []

            # Download original file given a blob path like "/folder1/folder2/file.pdf"
            orig_path = match.iloc[0].get(CSV_COL_ORIGINAL_FILE_PATH)
            if isinstance(orig_path, str) and orig_path:
                blob_name = orig_path.strip('/')
                local_orig = os.path.join(ARTIFACTS_DIR, os.path.basename(blob_name) or 'orig_file')
                try:
                    download_file_from_gcs(GCS_BUCKET_NAME, blob_name, local_orig, GCS_SERVICE_ACCOUNT_KEY_PATH)
                    original_text = text_extraction(local_orig) or ""
                except Exception as e:
                    print(f"Warning: failed to fetch original from GCS {blob_name}: {e}")

            # Download and append all corrigendum files from JSON list of dict values
            raw_corr = match.iloc[0].get(CSV_COL_CORRIGENDUM)
            
            try:
                corr_list = json.loads(raw_corr) if isinstance(raw_corr, str) and raw_corr else []
            except Exception:
                corr_list = []
            file_paths: List[str] = []
            
            for item in corr_list:
                if isinstance(item, dict):
                    for v in item.values():
                        if isinstance(v, str):
                            file_paths.append(v)
                elif isinstance(item, str):
                    file_paths.append(item)
            
            for idx, pth in enumerate(file_paths):
                try:
                    blob_name = pth.strip('/')
                    local_corr = os.path.join(ARTIFACTS_DIR, os.path.basename(blob_name) or f'corr_{idx}')
                    download_file_from_gcs(GCS_BUCKET_NAME, blob_name, local_corr, GCS_SERVICE_ACCOUNT_KEY_PATH)
                    t = text_extraction(local_corr)
                    if t:
                        corrigenda_texts.append(t)
                except Exception as e:
                    print(f"Warning: failed to fetch corrigendum from GCS {pth}: {e}")

            # Build combined text: original + all corrigenda + current
            segments: List[str] = []
            if original_text:
                segments.append(original_text)
            segments.extend([s for s in corrigenda_texts if s])
            if text:
                segments.append(text)
            combined_text = "\n\n".join(segments).strip()
            # Update text variables
            if combined_text:
                text = combined_text
                rfp['text'] = text

        # Use text for summarisation input
        summary_input_text = text.strip() if text else ""
        summariser = Summariser()
        tech_summary, tech_similarity, doc_summary, doc_similarity = summariser.summariser_pipeline(summary_input_text, file_name) if summary_input_text else ""

        # Tag relevant RMs
        try:
            relevant_rms = get_relevant_rms(tech_summary) or []
            ## Filter here
        except Exception:
            relevant_rms = []

        # Map relevant RM IDs to names from artifacts/rms.json
        relevant_rm_names: List[str] = []
        try:
            rm_json_path = os.path.join(ARTIFACTS_DIR, "rm_profiles.json")
            with open(rm_json_path, "r") as f:
                rm_dir = json.load(f)  # expected: list of {"rm_id": ..., "rm_name": ...}
            id_to_name = {}
            for item in rm_dir if isinstance(rm_dir, list) else []:
                rid = item.get("rm_id")
                rname = item.get("rm_name")
                if rid is not None and rname:
                    id_to_name[str(rid)] = rname
            relevant_rm_names = [id_to_name[str(rid)] for rid in relevant_rms if str(rid) in id_to_name]
            rfp["relevant_rm_names"] = relevant_rm_names
        except Exception as e:
            print(f"Warning: failed to map relevant RM IDs to names: {e}")
            relevant_rm_names = []

        # Update tracker with new rules
        opening_date = rfp.get('opening_date') or str(start_dt)
        match_internal_id = rfp.get('match_internal_id') or generate_rfp_id(rfp)
        dest_blob = None
        if local_file and match_internal_id and file_name:
            dest_blob = f"rfp_details/{match_internal_id}/{file_name}"

        # Helper to append a dict to JSON list in a cell
        def _append_corrigendum(json_cell, key: str, value: str) -> str:
            try:
                data = json.loads(json_cell) if isinstance(json_cell, str) and json_cell else []
                if not isinstance(data, list):
                    data = []
            except Exception:
                data = []
            data.append({key: value})
            return json.dumps(data)

        # Helper to upload local_file (if any) and update tracker row with path and appended corrigendum value
        def _upload_and_update(mask_int, corr_value: str, tech_summary_dest_blob, doc_summary_dest_blob):
            if dest_blob:
                try:
                    upload_file_to_gcs(local_file, GCS_BUCKET_NAME, dest_blob, GCS_SERVICE_ACCOUNT_KEY_PATH)
                except Exception as e:
                    print(f"Warning: failed to upload file to GCS: {e}")
            if mask_int.any():

                needed_index = tracker_df.index[mask_int].to_list() 
                idx = needed_index[0]

                rm_names_str = json.dumps(relevant_rm_names) if isinstance(relevant_rm_names, list) else (relevant_rm_names or "")
                cap_comp_str = json.dumps(tech_similarity) if isinstance(tech_similarity, dict) else (tech_similarity or "")
                doc_comp_str = json.dumps(doc_similarity) if isinstance(doc_similarity, dict) else (doc_similarity or "")
                due_dates_str = json.dumps(due_dates) if isinstance(due_dates, (list, dict)) else (due_dates or "")

                if dest_blob:
                    tracker_df.loc[idx, CSV_COL_ORIGINAL_FILE_PATH] = dest_blob
                existing = tracker_df.loc[mask_int, CSV_COL_CORRIGENDUM].iloc[0] if mask_int.any() else ""
                tracker_df.loc[idx, CSV_COL_RELEVANT_RMS] = rm_names_str
                tracker_df.loc[idx, CSV_COL_CAPABILITY_COMPARISON] = cap_comp_str
                tracker_df.loc[idx, CSV_COL_DOCUMENT_COMPARISON] = doc_comp_str
                tracker_df.loc[idx, CSV_COL_DUE_DATES] = due_dates_str
                tracker_df.loc[idx, CSV_COL_SUMMARY_LINK] = tech_summary_dest_blob
                tracker_df.loc[idx, CSV_COL_CORRIGENDUM] = _append_corrigendum(existing, opening_date, corr_value)

        tech_summary_file_name = f"artifacts/{match_internal_id}_{yday}_tech_summary.txt"
        with open(tech_summary_file_name, "w") as f:
            f.write(tech_summary)
        tech_summary_dest_blob = f"rfp_details/{match_internal_id}/{tech_summary_file_name}"
        upload_file_to_gcs(tech_summary_file_name, GCS_BUCKET_NAME, tech_summary_dest_blob, GCS_SERVICE_ACCOUNT_KEY_PATH)

        doc_summary_file_name = f"artifacts/{match_internal_id}_{yday}_doc_summary.txt"
        with open(doc_summary_file_name, "w") as f:
            f.write(doc_summary)
        doc_summary_dest_blob = f"rfp_details/{match_internal_id}/{doc_summary_file_name}"
        upload_file_to_gcs(doc_summary_file_name, GCS_BUCKET_NAME, doc_summary_dest_blob, GCS_SERVICE_ACCOUNT_KEY_PATH)              

        # Case 1: explicit 'corregendum' > 0
        if ('corregendum' in rfp) and rfp.get('corregendum'):
            try:
                corr_val = int(str(rfp.get('corregendum')).strip())
            except Exception:
                corr_val = 0
            if corr_val > 0 and match_internal_id:
                mask_int = tracker_df[CSV_COL_INTERNAL_ID] == match_internal_id
                _upload_and_update(mask_int, "", tech_summary_dest_blob, doc_summary_dest_blob)
                # Done with this RFP row update
                continue

        # Case 2: inferred is_corrigendum True
        if rfp.get('is_corrigendum') is True and match_internal_id:
            mask_int = tracker_df[CSV_COL_INTERNAL_ID] == match_internal_id
            _upload_and_update(mask_int, dest_blob or "", tech_summary_dest_blob, doc_summary_dest_blob)
            continue

        # Case 3: new entry (no/false corrigendum)
        # if extracted_external_id:
        row = {
            CSV_COL_EXTERNAL_ID: extracted_external_id,
            CSV_COL_RELEVANT_RMS: ",".join(relevant_rm_names) if relevant_rm_names else "",
            CSV_COL_RM: "",
            CSV_COL_CAPABILITY_COMPARISON: tech_similarity,
            CSV_COL_DOCUMENT_COMPARISON: doc_similarity,
            CSV_COL_DUE_DATES: due_dates,
            CSV_COL_CORRIGENDUM: [],
            CSV_COL_SUMMARY_LINK: "",
            CSV_COL_TITLE: title,
        }

        if not match_internal_id:
            match_internal_id = generate_rfp_id(rfp)
        row[CSV_COL_INTERNAL_ID] = match_internal_id

        path = upload_file_to_gcs(local_file, GCS_BUCKET_NAME, f"rfp_details/{match_internal_id}/{file_name}", GCS_SERVICE_ACCOUNT_KEY_PATH)
        row[CSV_COL_ORIGINAL_FILE_PATH] = path

        tracker_df = pd.concat([tracker_df, pd.DataFrame([row])], ignore_index=True)

    # Save tracker CSV back to GCS
    save_tracker_df(tracker_df)

    print("Pipeline finished")


if __name__ == "__main__":
    main()

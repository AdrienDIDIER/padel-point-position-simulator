#!/usr/bin/env python3
"""Scrapes latest padel rankings from padelmagazine.fr and generates data.json / players_*.json"""

import requests
from bs4 import BeautifulSoup
import tabula
import pandas as pd
import json
import os
import re
import tempfile
from datetime import datetime

BASE_URL = "https://padelmagazine.fr/classement-padel/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _pdf_date(url):
    """Extract (year, month) from a WordPress upload URL like .../uploads/2026/04/..."""
    m = re.search(r"/uploads/(\d{4})/(\d{2})/", url)
    if m:
        return int(m.group(1)), int(m.group(2))
    return (0, 0)


def fetch_pdf_urls():
    """Scrape padelmagazine.fr to find the LATEST ranked-by-position PDF URLs."""
    resp = requests.get(BASE_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    all_pdfs = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf") and "wp-content" in href:
            label = a.get_text(strip=True).lower()
            year, month = _pdf_date(href)
            all_pdfs.append((year, month, href, label))

    if not all_pdfs:
        raise ValueError("No PDFs found on padelmagazine.fr")

    # Sort by actual (year, month) extracted from the URL — newest first
    all_pdfs.sort(key=lambda x: (x[0], x[1]), reverse=True)
    latest_year, latest_month = all_pdfs[0][0], all_pdfs[0][1]
    print(f"  Latest data available: {latest_year}/{latest_month:02d}")

    # Only consider PDFs from the most recent month
    recent = [(href, label) for (y, m, href, label) in all_pdfs
              if y == latest_year and m == latest_month]
    # Fallback: include previous month if fewer than 2 PDFs this month
    if len(recent) < 2:
        prev_m = latest_month - 1 if latest_month > 1 else 12
        prev_y = latest_year if latest_month > 1 else latest_year - 1
        recent += [(href, label) for (y, m, href, label) in all_pdfs
                   if y == prev_y and m == prev_m]

    men_url = women_url = None
    for url, label in recent:
        url_l = url.lower()
        is_men    = any(k in url_l or k in label for k in ["messieu", "homme", "masculin"])
        is_women  = any(k in url_l or k in label for k in ["dame", "femme", "feminin"])
        is_ranked = any(k in url_l or k in label for k in ["rang", "rank"])

        if not men_url and is_ranked and is_men:
            men_url = url
        if not women_url and is_ranked and is_women:
            women_url = url
        if men_url and women_url:
            break

    # Broader fallback: any PDF from the latest month that fits gender
    if not men_url or not women_url:
        for url, label in recent:
            url_l = url.lower()
            is_women = any(k in url_l or k in label for k in ["dame", "femme", "feminin"])
            if not men_url and not is_women:
                men_url = url
            if not women_url and is_women:
                women_url = url
            if men_url and women_url:
                break

    return men_url, women_url


def download_pdf(url, dest):
    print(f"  Downloading: {url}")
    r = requests.get(url, timeout=120, stream=True, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)


def process_pdf(path):
    """Extract and clean ranking data from a TenUP PDF."""
    print(f"  Parsing: {path}")
    tables = tabula.read_pdf(
        path,
        pages="all",
        multiple_tables=True,
        lattice=False,
        stream=True,
        pandas_options={"header": 0, "dtype": str},
        silent=True,
    )
    if not tables:
        raise ValueError("No tables extracted from PDF")

    df = pd.concat([t for t in tables if not t.empty], ignore_index=True)
    df.columns = [str(c).strip() for c in df.columns]
    print(f"  Rows: {len(df)}, Columns: {list(df.columns)}")

    # Identify key columns by matching common TenUP PDF column names
    cols = {c.lower(): c for c in df.columns}

    def find_col(*keywords):
        for kw in keywords:
            for k, v in cols.items():
                if kw in k:
                    return v
        return None

    pos_col = find_col("rang", "position", "rank", "classement")
    pts_col = find_col("point", "pts")
    lic_col = find_col("licen")
    nom_col = find_col("nom")
    prenom_col = find_col("prenom", "prénom")

    return df, {"position": pos_col, "points": pts_col, "license": lic_col, "lastname": nom_col, "firstname": prenom_col}


def to_int(series):
    return pd.to_numeric(series.astype(str).str.replace(r"[^\d]", "", regex=True), errors="coerce")


def build_position_lookup(df, col_map):
    """Returns [[position, points], ...] sorted by position."""
    pos_col = col_map.get("position")
    pts_col = col_map.get("points")

    if not pos_col or not pts_col:
        # Auto-detect: find two numeric columns
        numeric_cols = [c for c in df.columns if to_int(df[c]).notna().sum() > len(df) * 0.4]
        if len(numeric_cols) >= 2:
            pos_col, pts_col = numeric_cols[0], numeric_cols[-1]
        else:
            raise ValueError(f"Cannot identify position/points columns. Got: {list(df.columns)}")

    df = df.copy()
    df["_pos"] = to_int(df[pos_col])
    df["_pts"] = to_int(df[pts_col])

    valid = df[(df["_pos"] > 0) & (df["_pts"] > 0)].dropna(subset=["_pos", "_pts"])
    valid = valid.sort_values("_pts", ascending=False).drop_duplicates("_pos").sort_values("_pos")
    result = [[int(r["_pos"]), int(r["_pts"])] for _, r in valid.iterrows()]
    print(f"  Position lookup: {len(result)} entries, range {result[0]} → {result[-1]}")
    return result


def build_player_lookup(df, col_map):
    """Returns {license: {n: name, p: points}} for all valid players."""
    lic_col = col_map.get("license")
    pts_col = col_map.get("points")
    if not lic_col or not pts_col:
        return {}

    df = df.copy()
    df["_pts"] = to_int(df[pts_col])
    df["_lic"] = df[lic_col].astype(str).str.strip()

    players = {}
    for _, row in df.iterrows():
        lic = row["_lic"]
        pts = row["_pts"]
        if not lic or lic in ("nan", "") or pd.isna(pts) or pts <= 0:
            continue

        parts = []
        if col_map.get("lastname"):
            parts.append(str(row.get(col_map["lastname"], "")).strip())
        if col_map.get("firstname"):
            parts.append(str(row.get(col_map["firstname"], "")).strip())
        name = " ".join(p for p in parts if p and p.lower() != "nan")
        players[lic] = {"n": name, "p": int(pts)}

    print(f"  Player lookup: {len(players)} players")
    return players


def process_gender(url, gender, result, players_out, tmpdir):
    if not url:
        print(f"  No URL for {gender}, skipping.")
        return

    pdf_path = os.path.join(tmpdir, f"{gender}.pdf")
    try:
        download_pdf(url, pdf_path)
        df, col_map = process_pdf(pdf_path)
        result[gender] = build_position_lookup(df, col_map)
        players_out[gender] = build_player_lookup(df, col_map)
    except Exception as e:
        print(f"  ERROR ({gender}): {e}")


def main():
    print("=== Padel Rankings Updater ===")
    print(f"Date: {datetime.now().isoformat()}")

    print("\nFetching PDF URLs...")
    men_url, women_url = fetch_pdf_urls()
    print(f"  Men:   {men_url}")
    print(f"  Women: {women_url}")

    result = {"updated": datetime.now().strftime("%Y-%m-%d"), "men": [], "women": []}
    players = {"men": {}, "women": {}}

    with tempfile.TemporaryDirectory() as tmpdir:
        print("\nProcessing men's rankings...")
        process_gender(men_url, "men", result, players, tmpdir)
        print("\nProcessing women's rankings...")
        process_gender(women_url, "women", result, players, tmpdir)

    # Fallback to existing data.xlsx if scrape failed for men
    if not result["men"]:
        xlsx_path = os.path.join(ROOT, "data.xlsx")
        if os.path.exists(xlsx_path):
            print("\nFalling back to data.xlsx for men's data...")
            try:
                df = pd.read_excel(xlsx_path)
                df.columns = [str(c).strip() for c in df.columns]
                col_map = {"position": "Position", "points": "Points"}
                result["men"] = build_position_lookup(df, col_map)
            except Exception as e:
                print(f"  Fallback failed: {e}")

    # Save data.json
    out = os.path.join(ROOT, "data.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    print(f"\nSaved data.json ({os.path.getsize(out):,} bytes)")

    # Save player lookup files
    for gender, data in players.items():
        if data:
            path = os.path.join(ROOT, f"players_{gender}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
            print(f"Saved players_{gender}.json ({os.path.getsize(path):,} bytes)")

    print("\nDone.")


if __name__ == "__main__":
    main()

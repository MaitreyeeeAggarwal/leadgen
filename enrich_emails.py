import os
import re
import csv
import sys
import asyncio
import httpx
import pandas as pd

# Reconfigure stdout for UTF-8 compatibility
sys.stdout.reconfigure(encoding='utf-8')

# Add folder path to sys.path to allow imports if run from outside
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modular components
from email_crawler import scrape_emails_for_site
from run_pipeline import query_nemotron_async, load_env_file

load_env_file()
api_key = os.environ.get("NVIDIA_API_KEY")

async def enrich_csv(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return
        
    print(f"Reading leads from '{file_path}' for email enrichment...")
    
    # Read all rows
    rows = []
    with open(file_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
            
    total_leads = len(rows)
    to_enrich = [r for r in rows if not r.get("Email") or r["Email"] == ""]
    
    print(f"Total leads: {total_leads}")
    print(f"Leads needing email enrichment: {len(to_enrich)}")
    
    if not to_enrich:
        print("All leads already have emails. Nothing to do!")
        return
        
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
    
    async with httpx.AsyncClient(limits=limits) as client:
        for idx, row in enumerate(to_enrich):
            name = row.get("Business Name", "")
            website = row.get("Website", "")
            phone = row.get("Phone Number", "")
            
            # Use placeholder address since we only have Name, Phone, and Web from the raw log
            address = "" 
            
            print(f"[{idx+1}/{len(to_enrich)}] Enriching: '{name}'")
            
            emails_found = []
            if website and website != "nan" and website.strip():
                try:
                    emails_found = await scrape_emails_for_site(client, website)
                except Exception as e:
                    print(f"    => Crawl error: {e}")
                    
            if emails_found:
                row["Email"] = emails_found[0]
                print(f"    => Found Email via crawl: {emails_found[0]}")
            else:
                if api_key:
                    # Fallback to AI Nemotron
                    try:
                        ai_email = await query_nemotron_async(client, name, website, phone, address)
                        if ai_email and ai_email != "NOT_FOUND":
                            row["Email"] = ai_email
                            print(f"    => Inferred Email via AI: {ai_email}")
                        else:
                            row["Email"] = "NOT_FOUND"
                            print("    => Email NOT_FOUND")
                    except Exception as e:
                        row["Email"] = "NOT_FOUND"
                        print(f"    => AI error: {e}")
                else:
                    row["Email"] = "NOT_FOUND"
                    print("    => Email NOT_FOUND (AI key not set)")
            
            # Save progress in real-time by rewriting the file
            for attempt in range(10):
                try:
                    with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)
                    break
                except PermissionError:
                    if attempt == 0:
                        print(f"[Warning] Permission denied. Close the file if open in Excel. Retrying...")
                    await asyncio.sleep(2)
                    
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    csv_file = input("Enter the CSV file name to enrich [default: AssetF.csv]: ").strip()
    if not csv_file:
        csv_file = "AssetF.csv"
        
    asyncio.run(enrich_csv(csv_file))

import os
import re
import csv
import sys
import json
import asyncio
import httpx
import pandas as pd
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# Reconfigure stdout to use UTF-8 to prevent UnicodeEncodeErrors on Windows terminals
sys.stdout.reconfigure(encoding='utf-8')

# Import our modular components
from stealth_maps_scraper import scrape_query_stealth
from email_crawler import scrape_emails_for_site

def load_env_file():
    """Loads environment variables from local or home .env files."""
    env_paths = [".env", os.path.expanduser("~/.env")]
    for path in env_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()

# Initialize environment
load_env_file()
api_key = os.environ.get("NVIDIA_API_KEY")

async def generate_regions_async(client, country_name):
    """Asks the reasoning model to partition a country into its top 40 commercial regions/cities/suburbs."""
    if not api_key:
        print("[Warning] NVIDIA_API_KEY is missing. Defaulting to searching the country name itself.")
        return [country_name]
        
    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    prompt = f"""You are a geographical database.
Generate a clean JSON list containing the 40 most populous or commercially significant cities, suburbs, or regions in the country '{country_name}'.
The output must be a valid JSON array of strings, for example:
[
  "Sydney, NSW",
  "Melbourne, VIC"
]
Do not include any introductory or concluding text. Return ONLY the raw JSON array. Keep regions localized so we can search Google Maps within them."""

    payload = {
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        "max_tokens": 1024,
        "reasoning_budget": 512,
        "stream": False,
        "temperature": 0.1,
        "top_p": 0.95
    }
    
    print(f"Querying NVIDIA Nemotron to partition '{country_name}' into sub-regions...")
    try:
        response = await client.post(invoke_url, headers=headers, json=payload, timeout=45.0)
        if response.status_code != 200:
            print(f"API Error generating regions: {response.text}. Defaulting to whole country.")
            return [country_name]
            
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        # Extract JSON array
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            content = match.group(0)
            
        regions = json.loads(content)
        if isinstance(regions, list) and len(regions) > 0:
            print(f"Successfully generated {len(regions)} sub-regions for {country_name}.")
            return regions
    except Exception as e:
        print(f"Failed to parse generated sub-regions: {e}. Defaulting to whole country.")
        
    return [country_name]

async def query_nemotron_async(client, name, website, phone, address):
    """Queries nvidia/nemotron-3-nano-omni-30b-a3b-reasoning asynchronously."""
    if not api_key:
        return None
        
    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    prompt = f"""You are an assistant specializing in business directory research.
Find the public contact email address for the following business.

Business Details:
- Name: {name}
- Website: {website if pd.notna(website) and website else "Not provided"}
- Phone: {phone if pd.notna(phone) and phone else "Not provided"}
- Address: {address if pd.notna(address) and address else "Not provided"}

Instructions:
1. Use your knowledge base and reasoning to identify the correct public email address for this business.
2. If the website is provided, think about what the email would be based on the domain (e.g. if the website is 'http://example.com.au', the email is likely 'info@example.com.au' or similar).
3. Be concise in your reasoning.
4. At the very end of your response, output a line in the exact format:
   Email: <email_address>
   If you cannot find or confidently infer any email, output:
   Email: NOT_FOUND"""

    payload = {
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        "max_tokens": 1024,
        "reasoning_budget": 512,
        "stream": False,
        "temperature": 0.2,
        "top_p": 0.95
    }
    
    for attempt in range(3):
        try:
            response = await client.post(invoke_url, headers=headers, json=payload, timeout=45.0)
            if response.status_code in [429, 503]:
                await asyncio.sleep(4 * (attempt + 1))
                continue
            if response.status_code != 200:
                return None
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            match = re.search(r"Email:\s*([^\s\n]+)", content, re.IGNORECASE)
            if match:
                email_val = match.group(1).strip()
                if email_val.upper() == "NOT_FOUND":
                    return "NOT_FOUND"
                if "@" in email_val and "." in email_val:
                    return email_val
                else:
                    all_emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", content)
                    if all_emails:
                        return all_emails[0]
            return "NOT_FOUND"
        except Exception:
            await asyncio.sleep(2)
    return None

async def main():
    print("====================================================")
    print("      AUTOMATED LEAD SCRAPER & AI PIPELINE")
    print("====================================================")
    
    # Interactive Prompts
    query_type = input("Enter the type of companies to search for (e.g. Dentists): ").strip()
    while not query_type:
        query_type = input("Company type cannot be empty. Please enter (e.g. Dentists): ").strip()
        
    country = input("Enter the country to search in (e.g. Australia): ").strip()
    while not country:
        country = input("Country cannot be empty. Please enter (e.g. Australia): ").strip()
        
    keywords_raw = input("Enter comma-separated keywords to filter categories (or press Enter to skip filtering): ").strip()
    filter_keywords = [k.strip().lower() for k in keywords_raw.split(",") if k.strip()] if keywords_raw else None
    
    output_csv = input("Enter output CSV file name [default: scraped_leads.csv]: ").strip()
    if not output_csv:
        output_csv = "scraped_leads.csv"
        
    print("\n----------------------------------------------------")
    print(f"Company Type:    {query_type}")
    print(f"Country:         {country}")
    print(f"Filter Whitelist: {filter_keywords if filter_keywords else 'None (Scraping all categories)'}")
    print(f"Output File:     {output_csv}")
    print("----------------------------------------------------\n")
    
    if not api_key:
        print("[Warning] NVIDIA_API_KEY is not configured in ~/.env. The pipeline will fall back to website scraping only, without AI lookups.")

    # 1. Generate Sub-regions
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
    async with httpx.AsyncClient(limits=limits) as client:
        regions = await generate_regions_async(client, country)
        
    print(f"\nBeginning pipeline for {len(regions)} regions in {country}...\n")

    # Load existing leads for deduplication
    existing_leads = set()
    if os.path.exists(output_csv):
        try:
            df_old = pd.read_csv(output_csv)
            for _, row in df_old.iterrows():
                name = str(row.get("Business Name", "")).strip().lower()
                phone = str(row.get("Phone Number", "")).strip().lower()
                if name:
                    existing_leads.add((name, phone))
            print(f"Loaded {len(existing_leads)} existing leads from '{output_csv}' for deduplication.")
        except Exception as e:
            print(f"Could not load existing file: {e}. Starting fresh.")

    # Loop through each sub-region
    for r_idx, region in enumerate(regions):
        print(f"\n====================================================")
        print(f" [{r_idx+1}/{len(regions)}] REGION: {region}")
        print(f"====================================================")
        
        search_query = f"{query_type} in {region}"
        
        # 2. Start Google Maps Scraper for this region
        print(f"Step 1: Scraping Google Maps for '{search_query}'...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-gpu", "--no-sandbox"]
            )
            context = await browser.new_page()
            raw_listings = await scrape_query_stealth(context, search_query)
            await browser.close()
            
        if not raw_listings:
            print(f"No listings found on Google Maps for '{region}'. Moving to next region.")
            continue
            
        print(f"Scraped {len(raw_listings)} raw listings in '{region}'.")
        
        # 3. Filter & Enrich Listings
        print(f"Step 2: Filtering and Enriching leads in '{region}'...")
        
        new_leads = []
        
        async with httpx.AsyncClient(limits=limits) as client:
            for idx, item in enumerate(raw_listings):
                name = item.get("Business Name", "")
                phone = item.get("Phone Number", "")
                category = item.get("Industry", "")
                website = item.get("Website", "")
                
                # Deduplicate
                key = (name.strip().lower(), phone.strip().lower())
                if key in existing_leads:
                    continue
                    
                # Filter Category
                if filter_keywords and category:
                    category_lower = category.lower()
                    if not any(kw in category_lower for kw in filter_keywords):
                        continue
                        
                print(f"  [{idx+1}/{len(raw_listings)}] Processing: '{name}'")
                
                # Crawl Website First
                emails_found = []
                if website and pd.notna(website):
                    emails_found = await scrape_emails_for_site(client, website)
                    
                if emails_found:
                    item["Email"] = emails_found[0]
                    print(f"    => Found Email via crawl: {emails_found[0]}")
                else:
                    # Fallback to AI Nemotron
                    # Construct address from memory (critical context for AI)
                    addr1 = str(item.get("Address Line 1", "")) if pd.notna(item.get("Address Line 1")) else ""
                    addr2 = str(item.get("Address Line 2", "")) if pd.notna(item.get("Address Line 2")) else ""
                    address = f"{addr1} {addr2}".strip()
                    
                    ai_email = await query_nemotron_async(client, name, website, phone, address)
                    if ai_email and ai_email != "NOT_FOUND":
                        item["Email"] = ai_email
                        print(f"    => Inferred Email via AI: {ai_email}")
                    else:
                        item["Email"] = "NOT_FOUND"
                        print("    => Email NOT_FOUND")
                
                new_leads.append(item)
                existing_leads.add(key)
                
                # Save CSV (with retries for PermissionError if locked by Excel)
                # Before saving, clean up CSV columns (drop address and Google Maps links)
                df_new = pd.DataFrame(new_leads)
                
                # Remove requested columns
                cols_to_drop = ["Address Line 1", "Address Line 2", "Google Maps Link"]
                df_new_cleaned = df_new.drop(columns=[col for col in cols_to_drop if col in df_new.columns], errors="ignore")
                
                if os.path.exists(output_csv):
                    try:
                        df_old = pd.read_csv(output_csv)
                        df_final = pd.concat([df_old, df_new_cleaned], ignore_index=True)
                    except Exception:
                        df_final = df_new_cleaned
                else:
                    df_final = df_new_cleaned
                    
                # Save to output file
                for attempt in range(20):
                    try:
                        df_final.to_csv(output_csv, index=False, encoding="utf-8-sig")
                        break
                    except PermissionError:
                        if attempt == 0:
                            print(f"\n[Warning] Permission denied writing to '{output_csv}'. Is the file open in Excel? Please close it to save. Retrying every 3s...")
                        await asyncio.sleep(3)
                        
                # Clear incremental list for next iteration
                new_leads = []
                await asyncio.sleep(1)
                
        print(f"Region '{region}' complete. Leads appended directly to '{output_csv}'.")
        
    print(f"\nPipeline complete! Output saved to '{output_csv}'.")

if __name__ == "__main__":
    asyncio.run(main())

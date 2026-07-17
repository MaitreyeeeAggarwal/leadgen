# Automated Lead Scraper & AI Email Enrichment Pipeline

An end-to-end automated pipeline to scrape business listings from Google Maps, filter them by industry category, extract public contact email addresses via direct website crawling, and fall back to the **NVIDIA Nemotron Reasoning AI model** to infer or lookup missing emails.

---

## Features

1. **Strictly Interactive Prompts**: Just run the script, and it will prompt you for everything (company type, country, filter keywords, output file).
2. **AI Country Partitioning**: If you enter a country (e.g., `Australia`), the script queries the NVIDIA Nemotron model to dynamically generate the top 40 most populous commercial cities, suburbs, or regions in that country, running searches in each to bypass Google Maps' 120-listing query limit and extract maximum leads.
3. **Category-Based Filtering**: Restrict listings to relevant categories (e.g., searching for `Dentists` will filter out general doctors or orthodontists if you configure it to filter).
4. **Dual-Method Email Resolution**:
   * **Crawl First**: Attempts to scrape the listing's website homepage and top contact pages to find email addresses.
   * **AI Fallback**: If crawling fails, the script queries `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` to infer the email or fetch it from pre-training data.
5. **Clean Column Output**: Excludes raw address lines and Google Maps links, saving a clean dataset: `Business Name`, `Phone Number`, `Email`, `Website`, `Industry`, `Rating`, `Review Count`.
6. **Excel Write Protection**: Detects if the output CSV is open in Excel, displays a warning in the console, and retries saving every 3 seconds to prevent data loss.

---

## Installation & Setup

### 1. Prerequisites
Ensure you have **Python 3.10+** installed on your system.

### 2. Install Dependencies
Run the following command to install the required Python libraries:
```bash
pip install playwright beautifulsoup4 pandas httpx requests
```

### 3. Install Playwright Web Browser
Run the Playwright installer to download the Chromium browser executable:
```bash
playwright install chromium
```

---

## NVIDIA API Configuration

The AI fallback email search uses the `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` model. 

1. **Obtain an API Key**:
   * Visit the [NVIDIA API Catalog](https://build.nvidia.com/).
   * Sign up or log in, select the **Nemotron-3-Nano-Omni-30B-A3B-Reasoning** model, and click **Generate Key**.

2. **Save the Key Securely**:
   To keep your key safe from leakage into the code or terminal logs, store it in the `.env` file in your User Profile directory (`~/.env`).

   * **On Windows (PowerShell)**:
     Open PowerShell and run the following command. It will prompt you to enter the key securely (your typing will be hidden):
     ```powershell
     $val = Read-Host -AsSecureString "Enter NVIDIA_API_KEY"; $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($val); $Plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR); Add-Content -Path "$Home\.env" -Value "NVIDIA_API_KEY=$Plain"; Write-Host "Saved."
     ```

   * **On Mac / Linux (Bash/Zsh)**:
     Open your terminal and run:
     ```bash
     printf "Enter NVIDIA_API_KEY (typing hidden): " && read -s val && echo && echo "NVIDIA_API_KEY=$val" >> ~/.env && echo "Saved."
     ```

---

## How to Run

1. Open your terminal in the directory where the scripts are saved.
2. Run the pipeline script:
   ```bash
   python run_pipeline.py
   ```
3. Answer the interactive prompts:
   ```text
   ====================================================
         AUTOMATED LEAD SCRAPER & AI PIPELINE
   ====================================================
   Enter the type of companies to search for (e.g. Dentists): Dentists
   Enter the country to search in (e.g. Australia): Australia
   Enter comma-separated keywords to filter categories (or press Enter to skip filtering): dentist, dental
   Enter output CSV file name [default: scraped_leads.csv]: scraped_dentists.csv
   ```

---

## File Descriptions

* [run_pipeline.py](file:///c:/Users/maitr/.gemini/antigravity-ide/scratch/australia_accountants_scraper/run_pipeline.py): The main pipeline runner script.
* [stealth_maps_scraper.py](file:///c:/Users/maitr/.gemini/antigravity-ide/scratch/australia_accountants_scraper/stealth_maps_scraper.py): Contains the Playwright Google Maps search and scraping engine.
* [email_crawler.py](file:///c:/Users/maitr/.gemini/antigravity-ide/scratch/australia_accountants_scraper/email_crawler.py): Contains the BeautifulSoup4 and HTTPX website crawler.

---

## Troubleshooting

### 1. `PermissionError: [Errno 13] Permission denied`
* **Cause**: The output CSV file is open in Microsoft Excel or another CSV viewer. Excel locks the file exclusively, preventing the script from writing updates.
* **Solution**: Keep the script running! Close the file in Excel, and the script will automatically resume saving progress within 3 seconds.

### 2. `Playwright.helper.Error: Executable not found`
* **Cause**: Playwright web browsers have not been downloaded.
* **Solution**: Run `playwright install chromium` in your terminal.

### 3. AI Emails output `NOT_FOUND` or are skipped
* **Cause**: If the console displays `NVIDIA_API_KEY is not configured`, the script will bypass AI enrichment and save `NOT_FOUND` where crawling fails. 
* **Solution**: Follow the API Key configuration steps above to set your key.

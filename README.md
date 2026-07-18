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

### 🪟 Windows Setup (For Systems Without Python)

If you are on a fresh Windows machine, open **PowerShell** and run these commands step-by-step:

1. **Install Python 3.11** using Windows Package Manager (Winget):
   ```powershell
   winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
   ```
   > [!IMPORTANT]
   > Close your current PowerShell window and open a new one so that Windows recognizes the newly installed `python` command.

2. **Navigate to the scraper directory**:
   ```powershell
   cd path/to/australia_accountants_scraper
   ```
   *(Replace `path/to/...` with the actual folder path where you downloaded the repository.)*

3. **Create a virtual environment**:
   ```powershell
   python -m venv .venv
   ```

4. **Activate the virtual environment**:
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
   > [!NOTE]
   > If you get an execution policy error, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` first, then run the activation command again.

5. **Install Python dependencies** listed in [requirements.txt](file:///c:/Users/maitr/.gemini/antigravity-ide/scratch/australia_accountants_scraper/requirements.txt):
   ```powershell
   pip install -r requirements.txt
   ```

6. **Install the Playwright browser executable**:
   ```powershell
   playwright install chromium
   ```

7. **Run the lead scraper pipeline**:
   ```powershell
   python run_pipeline.py
   ```

---

### 🚀 Zero-Setup Master Prompt (For AI Chatbots)

If you prefer to have an AI assistant (like Gemini, ChatGPT, or Claude) walk you through the process, copy and paste this master prompt:

```text
I want to run a Python lead scraper project on my machine, but my system is brand new and does not have Python installed. 

My Operating System is: Windows 11

Please write a step-by-step guide and an automated shell script for my system to:
1. Check if Python 3.10+ is installed, and if not, install the latest Python 3.10+ (using Winget).
2. Help me open the terminal/PowerShell and navigate to the project directory.
3. Create a Python virtual environment (`.venv`) and activate it.
4. Install these python dependencies: playwright, beautifulsoup4, pandas, httpx, requests.
5. Run `playwright install chromium`.

Please explain clearly how to open the terminal, run the commands, and verify that everything is working.
```

---

### 💻 macOS & Linux Setup

If you already have Python 3.10+ installed and prefer doing it manually:

1. **Install Dependencies** listed in [requirements.txt](file:///c:/Users/maitr/.gemini/antigravity-ide/scratch/australia_accountants_scraper/requirements.txt):
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Playwright Web Browser**:
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

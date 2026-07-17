import asyncio
import re
import urllib.parse
from bs4 import BeautifulSoup
import httpx

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

async def fetch_page(client, url):
    """Fetch the page HTML, returning None if request fails."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = await client.get(url, headers=headers, timeout=12.0, follow_redirects=True)
        if response.status_code == 200:
            return response.text
    except Exception:
        pass
    return None

def is_valid_email(email):
    """Filters out asset file extensions and common test/mock/error reporting emails."""
    email = email.lower().strip()
    ignore_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.pdf', '.css', '.js', '.woff', '.woff2', '.webp', '.ico')
    junk_patterns = ['sentry', 'wixpress', 'example.com', 'mysite.com', 'yourdomain.com', 'email.com', 'domain.com', 'yourpaypalemail', 'your@email.com', 'user@domain.com', 'yourname', 'test@']
    
    if any(email.endswith(ext) for ext in ignore_extensions):
        return False
    if '.' not in email.split('@')[-1]:
        return False
    if re.search(r'[\\/:\*\?"<>\|]', email):
        return False
    if any(pat in email for pat in junk_patterns):
        return False
    return True

def extract_emails_from_text(text):
    """Search text using regex and filter out common false-positive static file endings and mock emails."""
    emails = re.findall(EMAIL_REGEX, text)
    valid_emails = []
    for email in emails:
        clean = email.lower().strip()
        if is_valid_email(clean) and clean not in valid_emails:
            valid_emails.append(clean)
    return valid_emails

def get_contact_links(homepage_url, html):
    """Identify subpages (e.g., contact/about) within the same domain to inspect next."""
    soup = BeautifulSoup(html, 'html.parser')
    links = []
    parsed_home = urllib.parse.urlparse(homepage_url)
    
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        absolute_url = urllib.parse.urljoin(homepage_url, href)
        parsed_abs = urllib.parse.urlparse(absolute_url)
        
        # Ensure the link is on the same domain
        if parsed_abs.netloc == parsed_home.netloc:
            link_text = a.get_text().lower()
            href_lower = href.lower()
            # Match keywords
            keywords = ['contact', 'about', 'team', 'enquire', 'support', 'connect', 'staff']
            if any(k in link_text or k in href_lower for k in keywords):
                if absolute_url not in links and absolute_url != homepage_url:
                    links.append(absolute_url)
                    
    return links[:3]  # Inspect at most 3 contact pages

async def scrape_emails_for_site(client, homepage_url):
    """Inspect homepage and contact subpages to extract emails."""
    if not homepage_url or not isinstance(homepage_url, str):
        return []
        
    homepage_url = homepage_url.strip()
    if not homepage_url.startswith('http'):
        homepage_url = 'https://' + homepage_url
        
    html = await fetch_page(client, homepage_url)
    if not html:
        # Fallback to http if https failed
        if homepage_url.startswith('https://'):
            homepage_url = homepage_url.replace('https://', 'http://')
            html = await fetch_page(client, homepage_url)
            
    if not html:
        return []
        
    # Check homepage
    emails = extract_emails_from_text(html)
    
    # Check mailto links on homepage
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href.lower().startswith('mailto:'):
            email = href[7:].split('?')[0].strip()
            if email:
                email_clean = email.split(',')[0].strip().lower()  # In case of multiple emails
                if is_valid_email(email_clean) and email_clean not in emails:
                    emails.append(email_clean)
                    
    if emails:
        return emails
        
    # If no email on homepage, search top contact pages
    contact_links = get_contact_links(homepage_url, html)
    for link in contact_links:
        contact_html = await fetch_page(client, link)
        if contact_html:
            contact_emails = extract_emails_from_text(contact_html)
            
            # Check mailto on contact page
            c_soup = BeautifulSoup(contact_html, 'html.parser')
            for a in c_soup.find_all('a', href=True):
                href = a['href'].strip()
                if href.lower().startswith('mailto:'):
                    email = href[7:].split('?')[0].strip()
                    if email:
                        email_clean = email.split(',')[0].strip().lower()
                        if is_valid_email(email_clean) and email_clean not in contact_emails:
                            contact_emails.append(email_clean)
                            
            for email in contact_emails:
                if email not in emails:
                    emails.append(email)
            
            if emails:
                break  # Stop crawl once emails are found to be efficient
                
    return emails

async def crawl_websites_main(urls_list):
    """Main function to run the website email crawler in parallel batches."""
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    async with httpx.AsyncClient(limits=limits, follow_redirects=True, verify=False) as client:
        results = {}
        batch_size = 10
        for i in range(0, len(urls_list), batch_size):
            batch = urls_list[i:i+batch_size]
            tasks = [scrape_emails_for_site(client, url) for url in batch]
            batch_results = await asyncio.gather(*tasks)
            for url, emails in zip(batch, batch_results):
                results[url] = emails
                print(f"URL: {url} -> Emails: {emails}")
            await asyncio.sleep(0.5)
        return results

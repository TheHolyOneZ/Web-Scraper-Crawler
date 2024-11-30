import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tkinter import messagebox, filedialog
import logging
import json
import sqlite3
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import random
import csv
from collections import deque
from pathlib import Path
from time import sleep
from datetime import datetime
import re
from queue import Queue
import threading
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.progress import Progress
from rich.theme import Theme
from rich.logging import RichHandler
from tqdm import tqdm

# Enhanced terminal styling
custom_theme = Theme({
    "info": "green",
    "warning": "yellow",
    "error": "red bold",
    "success": "green bold"
})

console = Console(theme=custom_theme)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[RichHandler(console=console, show_time=False)]
)

# Configure customtkinter with cyberpunk theme
import customtkinter as ctk
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class EnhancedWebCrawlerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("[ TheZ's SCRAPER/CRAWLER v2.0 ]")
        self.root.geometry("600x980")
        
        
        # Cyberpunk styling
        self.style = {
            "bg_color": "#000000",
            "fg_color": "#00ff00",
            "accent": "#ff0000",
            "font": ("Courier", 12)
        }
        
        self.root.configure(bg=self.style["bg_color"])
        self.root.iconbitmap("icon.ico") 
        self.root.resizable(False, False)

        # Enhanced crawling variables
        self.crawl_queue = Queue()
        self.result_queue = Queue()
        self.active_threads = []
        self.stop_event = threading.Event()
        self.crawled_links = set()
        self.failed_urls = set()
        self.results = []
        self.proxies = []
        self.download_dir = ""
        
        # Rate limiting and performance settings
        self.rate_limit = 10  # requests per second
        self.last_request_time = {}
        self.semaphore = asyncio.Semaphore(10)
        
        # Headers with rotating User-Agents
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        ]
        
        # Initialize database
        self.db_name = "scraper_results.db"
        self.init_database()
        
        # Build enhanced GUI
        self.build_cyberpunk_gui()
    def build_cyberpunk_gui(self):
          """Build enhanced cyberpunk-style GUI"""
          # Initialize all entry variables
          self.depth_entry = None
          self.threads_entry = None
          self.retry_entry = None
          self.keyword_entry = None
          self.filetype_filter_entry = None
          self.download_assets_enabled = ctk.BooleanVar(value=False)

          # Main frame with neon styling
          main_frame = ctk.CTkFrame(self.root, fg_color="#000000")
          main_frame.pack(fill="both", expand=True, padx=20, pady=20)

          # Title with matrix-style effect
          title_label = ctk.CTkLabel(
              main_frame,
              text="[ TheZ's SCRAPER/CRAWLER ]",
              font=("Courier", 24, "bold"),
              text_color="#00ff00"
          )
          title_label.pack(pady=20)

          # URL Input Section
          url_frame = ctk.CTkFrame(main_frame, fg_color="#0a0a0a")
          url_frame.pack(fill="x", padx=10, pady=5)
    
          self.url_entry = ctk.CTkEntry(
              url_frame,
              width=600,
              placeholder_text="Enter target URL...",
              font=("Courier", 12)
          )
          self.url_entry.pack(pady=10)

          # Control Panel
          control_frame = ctk.CTkFrame(main_frame, fg_color="#0a0a0a")
          control_frame.pack(fill="x", padx=10, pady=5)

          # Settings grid with proper initialization
          settings_grid = [
              ("Depth", "depth_entry", "3"),
              ("Threads", "threads_entry", "17"), # Increased threads 15-20
              ("Retries", "retry_entry", "3"),
              ("Keywords", "keyword_entry", ""),
              ("Filetypes", "filetype_filter_entry", ".pdf,.doc,.txt")
          ]

          for label_text, entry_name, default_val in settings_grid:
              frame = ctk.CTkFrame(control_frame, fg_color="#0a0a0a")
              frame.pack(fill="x", padx=5, pady=2)
        
              label = ctk.CTkLabel(
                  frame,
                  text=f"[{label_text}]:",
                  font=("Courier", 12),
                  text_color="#00ff00"
              )
              label.pack(side="left", padx=5)
        
              entry = ctk.CTkEntry(
                  frame,
                  width=100,
                  font=("Courier", 12)
              )
              entry.insert(0, default_val)
              entry.pack(side="left", padx=5)
              setattr(self, entry_name, entry)

          # Options Frame
          options_frame = ctk.CTkFrame(main_frame, fg_color="#0a0a0a")
          options_frame.pack(fill="x", padx=10, pady=5)

          # Download Assets Toggle
          self.download_toggle = ctk.CTkCheckBox(
              options_frame,
              text="Download Assets",
              variable=self.download_assets_enabled,
              font=("Courier", 12),
              text_color="#00ff00",
              fg_color="#00ff00"
          )
          self.download_toggle.pack(side="left", padx=5)

          # Action Buttons
          button_frame = ctk.CTkFrame(main_frame, fg_color="#0a0a0a")
          button_frame.pack(fill="x", padx=10, pady=5)

          buttons = [
              ("LAUNCH SCAN", self.start_crawling, "#00ff00"),
              ("LOAD PROXIES", self.load_proxies, "#00aaff"),
              ("SET OUTPUT DIR", self.set_download_directory, "#ff00ff")
          ]

          for text, command, color in buttons:
              btn = ctk.CTkButton(
                  button_frame,
                  text=text,
                  command=command,
                  font=("Courier", 12, "bold"),
                  fg_color=color,
                  hover_color="#1a1a1a"
              )
              btn.pack(side="left", padx=5, pady=5)

          # Progress Bar
          self.progress_bar = ctk.CTkProgressBar(
              main_frame,
              width=600,
              height=20,
              progress_color="#00ff00"
          )
          self.progress_bar.pack(pady=10)
          self.progress_bar.set(0)

          # Terminal Output
          self.result_box = ctk.CTkTextbox(
              main_frame,
              width=900,
              height=400,
              font=("Courier", 12),
              text_color="#00ff00",
              fg_color="#0a0a0a"
          )
          self.result_box.pack(pady=10)

          # Status Bar
          status_frame = ctk.CTkFrame(main_frame, fg_color="#0a0a0a")
          status_frame.pack(fill="x", padx=10, pady=5)
    
          self.status_label = ctk.CTkLabel(
              status_frame,
              text="[ READY ]",
              font=("Courier", 12),
              text_color="#00ff00"
          )
          self.status_label.pack(side="left", padx=5)

          # Save Results Button
          self.save_button = ctk.CTkButton(
              main_frame,
              text="SAVE RESULTS",
              command=self.save_results,
              font=("Courier", 12, "bold"),
              fg_color="#00ff00",
              hover_color="#1a1a1a"
          )
          self.save_button.pack(pady=10)


    def load_proxies(self):
        """Load proxy list from a file"""
        file_path = filedialog.askopenfilename(
            title="Select Proxy List",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
    
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    self.proxies = [line.strip() for line in file if line.strip()]
            
                self.log_to_gui(f"[ LOADED {len(self.proxies)} PROXIES ]")
                self.status_label.configure(text=f"[ {len(self.proxies)} PROXIES READY ]")
            
            # Validate proxy format
                valid_proxies = []
                for proxy in self.proxies:
                    if re.match(r'^(?:\d{1,3}\.){3}\d{1,3}:\d+$', proxy):
                        valid_proxies.append(proxy)
            
                self.proxies = valid_proxies
                self.log_to_gui(f"[ {len(valid_proxies)} VALID PROXIES ]")
            
            except Exception as e:
                self.log_to_gui(f"[ ERROR LOADING PROXIES: {str(e)} ]")

    def set_download_directory(self):
        """Set and create directory for downloaded assets"""
        selected_dir = filedialog.askdirectory(
            title="Select Download Directory",
            initialdir=os.getcwd()
        )
    
        if selected_dir:
            self.download_dir = selected_dir
            os.makedirs(self.download_dir, exist_ok=True)
        
            self.log_to_gui(f"[ OUTPUT DIR SET: {self.download_dir} ]")
            self.status_label.configure(text="[ OUTPUT DIRECTORY READY ]")
        
        # Create subdirectories for different asset types
            subdirs = ['images', 'css', 'js', 'documents']
            for subdir in subdirs:
                os.makedirs(os.path.join(self.download_dir, subdir), exist_ok=True)
            
            self.log_to_gui("[ ASSET DIRECTORIES INITIALIZED ]")

    def save_results(self):
        """Save crawled results to file with multiple format options"""
        file_path = filedialog.asksaveasfilename(
            title="Save Crawler Results",
            defaultextension=".json",
            filetypes=[
            ("JSON files", "*.json"),
            ("CSV files", "*.csv"),
            ("Text files", "*.txt")
            ]
        )
    
        if file_path:
            try:
                if file_path.endswith('.json'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(self.results, f, indent=4, ensure_ascii=False)
                    
                elif file_path.endswith('.csv'):
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=['url', 'title', 'description', 'fetched_on'])
                        writer.writeheader()
                        writer.writerows(self.results)
                    
                elif file_path.endswith('.txt'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        for result in self.results:
                            f.write(f"URL: {result['url']}\n")
                            f.write(f"Title: {result['title']}\n")
                            f.write(f"Description: {result['description']}\n")
                            f.write(f"Fetched: {result['fetched_on']}\n")
                            f.write("-" * 80 + "\n")
            
                self.log_to_gui(f"[ RESULTS SAVED TO: {file_path} ]")
                self.status_label.configure(text="[ RESULTS SAVED ]")
            
            except Exception as e:
                self.log_to_gui(f"[ ERROR SAVING RESULTS: {str(e)} ]")


    def init_database(self):
        """Initialize SQLite database with enhanced schema"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
        
        # Create an enhanced table structure
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT,
                description TEXT,
                headers TEXT,
                images TEXT,
                fetched_on TIMESTAMP,
                keywords TEXT,
                status_code INTEGER,
                content_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        
        # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_url ON results(url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fetched_on ON results(fetched_on)")
        
            conn.commit()
            logging.info("Database initialized successfully")
        
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")
        finally:
            conn.close()


    async def enhanced_crawl(self, urls, depth, threads, headers):
        """Enhanced crawling with better concurrency and rate limiting"""
        rate_limiter = asyncio.Semaphore(threads)
        visited = set()
        
        async def worker(url, current_depth):
            async with rate_limiter:
                if current_depth > depth or url in visited:
                    return
                    
                visited.add(url)
                try:
                    metadata = await self.fetch_links_with_retry(url, headers)
                    if metadata:
                        self.results.append(metadata)
                        self.save_to_database(metadata)
                        
                        tasks = []
                        for link in metadata['links']:
                            if link not in visited:
                                tasks.append(worker(link, current_depth + 1))
                        await asyncio.gather(*tasks)
                except Exception as e:
                    logging.error(f"Error crawling {url}: {e}")
        
        tasks = [worker(url, 0) for url in urls]
        await asyncio.gather(*tasks)

    async def fetch_links_with_retry(self, url, headers, max_retries=3):
        """Enhanced link fetching with retry mechanism"""
        for attempt in range(max_retries):
            try:
                proxy = random.choice(self.proxies) if self.proxies else None
                headers['User-Agent'] = random.choice(self.user_agents)
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers=headers,
                        proxy=proxy,
                        timeout=30
                    ) as response:
                        if response.status == 200:
                            html = await response.text()
                            metadata = self.parse_content(html, url)
                            
                            if self.download_assets_enabled.get():
                                await self.download_assets_async(metadata, url)
                                
                            return metadata
                            
                        elif response.status == 429:  # Rate limited
                            retry_after = int(response.headers.get('Retry-After', 60))
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            logging.warning(f"Status {response.status} for {url}")
                            return None
                            
            except Exception as e:
                if attempt == max_retries - 1:
                    logging.error(f"Failed after {max_retries} attempts: {url}")
                    self.failed_urls.add(url)
                    return None
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    def parse_content(self, html, url):
        """Enhanced content parsing with better extraction"""
        soup = BeautifulSoup(html, 'html.parser')
        
        metadata = {
            'url': url,
            'title': soup.title.string if soup.title else '',
            'description': '',
            'keywords': '',
            'links': set(),
            'images': set(),
            'scripts': set(),
            'styles': set(),
            'fetched_on': datetime.now().isoformat()
        }
        
        # Meta tags
        meta_tags = {
            'description': ('name', 'description'),
            'keywords': ('name', 'keywords'),
            'author': ('name', 'author'),
            'robots': ('name', 'robots')
        }
        
        for key, (attr, name) in meta_tags.items():
            meta = soup.find('meta', {attr: name})
            metadata[key] = meta.get('content', '') if meta else ''

        # Extract all resource types
        metadata['links'] = {urljoin(url, a['href']) for a in soup.find_all('a', href=True)}
        metadata['images'] = {urljoin(url, img['src']) for img in soup.find_all('img', src=True)}
        metadata['scripts'] = {urljoin(url, s['src']) for s in soup.find_all('script', src=True)}
        metadata['styles'] = {urljoin(url, s['href']) for s in soup.find_all('link', rel='stylesheet')}
        
        return metadata

    async def download_assets_async(self, metadata, base_url):
        """Asynchronous asset downloading"""
        if not self.download_dir:
            return

        domain = urlparse(base_url).netloc
        save_dir = Path(self.download_dir) / domain
        save_dir.mkdir(parents=True, exist_ok=True)

        async def download_file_async(url, subdir):
            try:
                file_path = save_dir / subdir / url.split('/')[-1]
                if file_path.exists():
                    return

                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.read()
                            file_path.parent.mkdir(parents=True, exist_ok=True)
                            file_path.write_bytes(content)
                            logging.info(f"Downloaded: {url}")
            except Exception as e:
                logging.error(f"Failed to download {url}: {e}")

        tasks = []
        for img_url in metadata['images']:
            tasks.append(download_file_async(img_url, 'images'))
        for css_url in metadata['styles']:
            tasks.append(download_file_async(css_url, 'css'))
        for js_url in metadata['scripts']:
            tasks.append(download_file_async(js_url, 'js'))

        await asyncio.gather(*tasks)

    def save_to_database(self, metadata):
        """Save results to SQLite database"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO results 
                (url, title, description, headers, images, fetched_on)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                metadata['url'],
                metadata['title'],
                metadata['description'],
                json.dumps(dict(metadata.get('headers', {}))),
                json.dumps(list(metadata['images'])),
                metadata['fetched_on']
            ))
            conn.commit()
        except Exception as e:
            logging.error(f"Database error: {e}")
        finally:
            conn.close()

    def start_crawling(self):
        """Initialize and start the crawling process"""
        try:
            url = self.url_entry.get().strip()
            if not url and not self.crawled_links:
                raise ValueError("No target URL specified")

            depth = int(self.depth_entry.get())
            threads = int(self.threads_entry.get())
            
            self.progress_bar.set(0)
            self.log_to_gui("[ INITIATING SCAN ]")
            
            asyncio.run(self.enhanced_crawl(
                [url] if url else list(self.crawled_links),
                depth,
                threads,
                {"User-Agent": random.choice(self.user_agents)}
            ))
            
            self.progress_bar.set(1)
            self.log_to_gui("[ SCAN COMPLETE ]")
            
        except Exception as e:
            self.log_to_gui(f"[ ERROR ] {str(e)}")
            logging.error(f"Crawling error: {e}")

    def log_to_gui(self, message):
        """Log messages to GUI with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.result_box.insert("end", f"[{timestamp}] {message}\n")
        self.result_box.see("end")

if __name__ == "__main__":
    root = ctk.CTk()
    app = EnhancedWebCrawlerApp(root)
    root.mainloop()

import chromadb
import aiohttp
import uuid
import re
import pandas as pd
import html
from bs4 import BeautifulSoup

class ScrapeANDSave:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path="./vector_db")
        # Creating a new collection as requested
        self.collection = self.chroma_client.get_or_create_collection(name="indusnet_website_v2")

    async def fetch_url(self, url):
        print(f"Fetching {url}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        text = await response.text()
                        soup = BeautifulSoup(text, "html.parser")
                        return {"status": 0, "data": soup, "message": ""}
                    else:
                        return {"status": -1, "data": None, "message": f"HTTP Error: {response.status}"}
        except Exception as e:
            return {"status": -1, "data": None, "message": str(e)}

    def clean_text(self, text):
        """Cleans raw text by removing HTML comments, entities, and extra noise."""
        if not text or not isinstance(text, str):
            return ""
        
        # Remove HTML comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        
        # Unescape HTML entities
        text = html.unescape(text)
        
        # Remove specific noise like "Edit Template" if it's common in the data
        text = text.replace("Edit Template", "")
        
        # Remove excessive whitespace and newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()

    async def clean_and_convert_to_markdown(self, soup):
        print("Cleaning and converting to Markdown...")

        # 1. Remove standard noise
        for tag in soup(["script", "style", "noscript", "iframe", "svg", "button", "input", "form"]):
            tag.decompose()

        # 2. Aggressive noise removal (Navbars, Footers, Sidebars often confuse RAG)
        main_content = soup.find('main')
        if main_content:    
            soup = main_content
        else:
            # If no <main>, try to remove common non-content areas manually
            for tag in soup.find_all(['header', 'footer', 'nav', 'aside']):
                tag.decompose()

        # 3. iterate over elements and format them as Markdown
        text_parts = []
        
        # We look for structural elements
        for element in soup.find_all(['h1', 'h2', 'h3', 'p', 'ul', 'ol', 'table', 'li']):
            
            # Skip if element has no text
            text = element.get_text(separator=" ", strip=True)
            if not text:
                continue

            # Add Markdown formatting
            if element.name == 'h1':
                text_parts.append(f"\n# {text}\n")
            elif element.name == 'h2':
                text_parts.append(f"\n## {text}\n")
            elif element.name == 'h3':
                text_parts.append(f"\n### {text}\n")
            elif element.name in ['ul', 'ol']:
                pass 
            elif element.name == 'li':
                text_parts.append(f"- {text}")
            elif element.name == 'p':
                text_parts.append(f"{text}\n")
            elif element.name == 'table':
                text_parts.append(f"\n[Table Data]: {text}\n")

        # Join everything into one big text block
        full_text = "\n".join(text_parts)
        
        # Remove excessive newlines
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)
        return full_text

    def create_overlapping_chunks(self, text, chunk_size=500, overlap=100):
        """Creates overlapping chunks of text."""
        print("Creating overlapping chunks...")

        if not text:
            return

        text_len = len(text)
        start = 0
        
        while start < text_len:
            end = start + chunk_size
            if end < text_len:
                cut_point = text.rfind(' ', start, end)
                if cut_point != -1 and cut_point > (start + chunk_size * 0.6):
                    end = cut_point + 1 # Include the space
            yield text[start:end]
            
            # Calculate next start position
            actual_chunk_len = end - start
            step = max(1, actual_chunk_len - overlap) 
            start += step

    async def save_batch(self, batch_ids, batch_docs, batch_metas):
        print(f"Saving batch of {len(batch_ids)} items...")
        if not batch_ids: return
        try:
            self.collection.add(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
        except Exception as e:
            print(f"Error saving batch: {e}")

    async def process_excel(self, file_path):
        """Reads Excel file and ingests raw_text into ChromaDB."""
        print(f"Processing Excel file: {file_path}")
        try:
            df = pd.read_excel(file_path)
            total_processed = 0
            
            for index, row in df.iterrows():
                url = row.get('url', 'unknown_url')
                raw_text = row.get('raw_text', '')
                
                if not raw_text:
                    print(f"Skipping empty text for URL: {url}")
                    continue
                
                print(f"Processing URL: {url}")
                clean_text = self.clean_text(raw_text)
                
                # Cleanup old data for this URL in the new collection if needed
                # (Though with v2, it's likely empty initially)
                try:
                    self.collection.delete(where={"url": url})
                except Exception:
                    pass

                batch_ids, batch_docs, batch_metas = [], [], []
                chunk_idx = 0
                
                for chunk in self.create_overlapping_chunks(clean_text, chunk_size=500, overlap=100):
                    # Using URL based ID: URL#chunk_number
                    chunk_id = f"{url}#{chunk_idx}"
                    batch_ids.append(chunk_id)
                    batch_docs.append(chunk)
                    batch_metas.append({"url": url})
                    chunk_idx += 1
                    
                    if len(batch_ids) >= 50:
                        await self.save_batch(batch_ids, batch_docs, batch_metas)
                        batch_ids, batch_docs, batch_metas = [], [], []

                if batch_ids:
                    await self.save_batch(batch_ids, batch_docs, batch_metas)
                
                total_processed += 1
                print(f"Finished processing {url} with {chunk_idx} chunks.")

            return {"status": 0, "message": "Success", "data": {"processed_urls": total_processed}}
            
        except Exception as e:
            print(f"Error processing Excel: {e}")
            return {"status": -1, "message": str(e)}

    async def process_url(self, url):
        # Keep old method for backward compatibility if needed, but update collection use
        try:
            fetch_res = await self.fetch_url(url)
            if fetch_res['status'] != 0:
                print(f"Error: {fetch_res['message']}")
                return

            soup = fetch_res['data']
            title = soup.title.string if soup.title else url
            clean_text = await self.clean_and_convert_to_markdown(soup)

            print(f"Purging old data for: {url}")
            try:
                self.collection.delete(where={"url": url})
            except Exception:
                pass
            
            batch_size = 50
            b_ids, b_docs, b_metas = [], [], []
            total_chunks = 0

            for chunk in self.create_overlapping_chunks(clean_text, chunk_size=500, overlap=100):
                b_ids.append(f"{url}#{total_chunks}")
                b_docs.append(chunk)
                b_metas.append({"url": url, "title": title})
                total_chunks += 1
                
                if len(b_ids) >= batch_size:
                    await self.save_batch(b_ids, b_docs, b_metas)
                    b_ids, b_docs, b_metas = [], [], []

            if b_ids:
                await self.save_batch(b_ids, b_docs, b_metas)

            return {"status": 0, "message": "Success", "data": {"chunks_count": total_chunks}}

        except Exception as e:
            print(f"Error: {e}")
            return {"status": -1, "message": str(e)}

if __name__ == "__main__":
    import asyncio
    import os
    
    scraper = ScrapeANDSave()
    excel_path = "./vector_db/website_extracted_data.xlsx"
    
    if os.path.exists(excel_path):
        print("Starting Excel Ingestion...")
        result = asyncio.run(scraper.process_excel(excel_path))
        print(f"\n--- INGESTION REPORT ---")
        print(f"Status: {'Success' if result['status'] == 0 else 'Failed'}")
        if result['status'] == 0:
            print(f"URLs Processed: {result['data']['processed_urls']}")
        else:
            print(f"Error: {result['message']}")
    else:
        print(f"Excel file not found at {excel_path}")

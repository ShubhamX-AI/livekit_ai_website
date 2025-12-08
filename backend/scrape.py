import chromadb
import aiohttp
import uuid
import re
from bs4 import BeautifulSoup

class ScrapeANDSave:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path="./vector_db")
        self.collection = self.chroma_client.get_or_create_collection(name="indusnet_website")

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
                # Lists are handled by their <li> children usually, 
                # but sometimes we just want the block. 
                # Let's rely on <li> loop or just raw text if logic is simple.
                pass 
            elif element.name == 'li':
                text_parts.append(f"- {text}")
            elif element.name == 'p':
                text_parts.append(f"{text}\n")
            elif element.name == 'table':
                # Tables are tricky, simply getting text usually works for basic RAG
                # unless you use a specific table parser.
                text_parts.append(f"\n[Table Data]: {text}\n")

        # Join everything into one big text block
        full_text = "\n".join(text_parts)
        
        # Remove excessive newlines
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)
        return full_text

    def create_overlapping_chunks(self, text, chunk_size=1000, overlap=200):
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

    async def save_batch(self,batch_ids, batch_docs, batch_metas):
        print("Saving batch...")
        if not batch_ids: return
        try:
            self.collection.add(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
        except Exception as e:
            print(f"Error saving batch: {e}")

    async def process_url(self, url):
        try:
            # 1. Fetch
            fetch_res = await self.fetch_url(url)
            if fetch_res['status'] != 0:
                print(f"Error: {fetch_res['message']}")
                return

            # 2. Process Text
            soup = fetch_res['data']
            title = soup.title.string if soup.title else url
            clean_text = await self.clean_and_convert_to_markdown(soup)

            # --- CRITICAL CHANGE: CLEAN UP OLD DATA ---
            print(f"Purging old data for: {url}")
            try:
                # This deletes any chunk where metadata 'url' matches the current url
                self.collection.delete(where={"url": url})
            except Exception as e:
                # If collection is empty or new, this might throw a harmless error or do nothing
                print(f"Note: Cleanup skipped or failed (might be new url): {e}")
            # ------------------------------------------
            
            print(f"Processing content length: {len(clean_text)}")

            # 3. Stream Chunks to DB (Batching)
            # We use lists to hold just a small batch (e.g., 50 items)
            batch_size = 50
            b_ids, b_docs, b_metas = [], [], []
            total_chunks = 0

            # Iterate over the GENERATOR
            for chunk in self.create_overlapping_chunks(clean_text, chunk_size=1000, overlap=200):
                b_ids.append(str(uuid.uuid4()))
                b_docs.append(chunk)
                b_metas.append({"url": url, "title": title})
                
                # If batch is full, save and clear RAM
                if len(b_ids) >= batch_size:
                    await self.save_batch(b_ids, b_docs, b_metas)
                    b_ids, b_docs, b_metas = [], [], [] # Clear memory
                    total_chunks += batch_size

            # Save remaining chunks
            if b_ids:
                await self.save_batch(b_ids, b_docs, b_metas)
                total_chunks += len(b_ids)

            return {"status": 0, "message": "Success", "data": {"chunks_count": total_chunks}}

        except Exception as e:
            print(f"Error: {e}")
            return {"status": -1, "message": str(e)}

    async def process_batch_urls(self, urls_list, concurrency_limit=5):
        semaphore = asyncio.Semaphore(concurrency_limit)

        async def limited_process(url):
            async with semaphore:
                return await self.process_url(url)

        # Create tasks
        tasks = [limited_process(url) for url in urls_list]
        
        print(f"Starting batch process for {len(urls_list)} URLs with concurrency {concurrency_limit}...")
        
        # Run all tasks
        results = await asyncio.gather(*tasks)

        # Generate Report
        summary = {
            "total": len(urls_list),
            "success": 0,
            "failed": 0,
            "details": results
        }

        for res in results:
            if res['status'] == 0:
                summary['success'] += 1
            else:
                summary['failed'] += 1

        return summary

if __name__ == "__main__":
    import asyncio
    scraper = ScrapeANDSave()

    # List of URLs to scrape
    my_urls = [
        "https://intglobal.com/",
        "https://intglobal.com/job-openings/",
        "https://intglobal.com/board-directors/",
        "https://intglobal.com/contact-us/",
        "https://intglobal.com/services/managed-services/" 
    ]
    
    # Run batch
    final_report = asyncio.run(scraper.process_batch_urls(my_urls))
    
    print("\n--- BATCH REPORT ---")
    print(f"Total: {final_report['total']}")
    print(f"Success: {final_report['success']}")
    print(f"Failed: {final_report['failed']}")
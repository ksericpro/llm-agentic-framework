from crawler_agent import CrawlerAgent
import time

def test_advanced_crawler():
    url = "https://www.guitargallery.com.sg/"
    print(f"\nStarting Advanced Crawl Test for: {url}")
    print("-" * 50)
    
    crawler = CrawlerAgent()
    
    start_time = time.time()
    result = crawler.scrape(url, max_chars=3000)
    end_time = time.time()
    
    print(f"\n✅ Finished in {end_time - start_time:.2f} seconds")
    print(f"Content Length: {len(result)}")
    print("\n--- CONTENT PREVIEW ---")
    print(result[:1500])
    print("\n--- END PREVIEW ---")

if __name__ == "__main__":
    test_advanced_crawler()

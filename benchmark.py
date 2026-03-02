import asyncio
import time
import argparse
import math
from collections import Counter

try:
    import aiohttp
    import numpy as np
except ImportError:
    print("Missing dependencies. Please run: pip install aiohttp numpy")
    exit(1)

async def make_request(session, url, payload, sem):
    async with sem:
        start_time = time.time()
        try:
            async with session.post(url, json=payload) as response:
                await response.read() # Read response completely
                status = response.status
        except Exception:
            status = 500
        end_time = time.time()
        return start_time, end_time, status

async def run_benchmark(url, num_requests, concurrency, payload):
    sem = asyncio.Semaphore(concurrency)
    
    # Using aiohttp ClientSession to send async HTTP requests
    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [make_request(session, url, payload, sem) for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
        
    return results

def print_stats(results, num_items_per_request):
    success_results = [r for r in results if r[2] == 200]
    failure_count = len(results) - len(success_results)
    
    if not success_results:
        print("No successful requests. Ensure the server is running.")
        return
        
    latencies = [(r[1] - r[0]) * 1000 for r in success_results] # convert to ms
    
    print("="*50)
    print("BENCHMARK RESULTS")
    print("="*50)
    print(f"Total Requests: {len(results)}")
    print(f"Successful:     {len(success_results)}")
    print(f"Failed:         {failure_count}")
    
    # ---------------------------------------------------------
    # Latency Stats
    # ---------------------------------------------------------
    print("\n--- Latency (ms) ---")
    print(f"Min:    {np.min(latencies):.2f} ms")
    print(f"25th:   {np.percentile(latencies, 25):.2f} ms")
    print(f"Median: {np.median(latencies):.2f} ms")
    print(f"Average:{np.mean(latencies):.2f} ms")
    print(f"75th:   {np.percentile(latencies, 75):.2f} ms")
    print(f"Max:    {np.max(latencies):.2f} ms")
    
    # ---------------------------------------------------------
    # Overall Throughput
    # ---------------------------------------------------------
    global_start = min(r[0] for r in success_results)
    global_end = max(r[1] for r in success_results)
    total_time = global_end - global_start
    
    overall_req_tps = len(success_results) / total_time
    overall_item_tps = (len(success_results) * num_items_per_request) / total_time
    
    print("\n--- Overall Throughput ---")
    print(f"Total Time:      {total_time:.2f} s")
    print(f"Requests/second: {overall_req_tps:.2f}")
    if num_items_per_request > 1:
        print(f"Items/second:    {overall_item_tps:.2f}")
    
    # ---------------------------------------------------------
    # Throughput Percentiles (Calculated over 1-second windows)
    # ---------------------------------------------------------
    # Group completed requests by the integer second they finished in
    second_bins = [math.floor(r[1] - global_start) for r in success_results]
    counts = Counter(second_bins)
    
    # Consider only full seconds (exclude the very last partial second to be accurate)
    max_full_sec = math.floor(total_time)
    
    if max_full_sec >= 2:
        # Get requests/sec array for every second
        tps_array = [counts.get(s, 0) for s in range(max_full_sec)]
        
        print("\n--- Throughput Distribution (Reqs/sec over 1s windows) ---")
        print(f"Min:    {np.min(tps_array):.2f} reqs/s")
        print(f"25th:   {np.percentile(tps_array, 25):.2f} reqs/s")
        print(f"Median: {np.median(tps_array):.2f} reqs/s")
        print(f"Average:{np.mean(tps_array):.2f} reqs/s")
        print(f"75th:   {np.percentile(tps_array, 75):.2f} reqs/s")
        print(f"Max:    {np.max(tps_array):.2f} reqs/s")
        
        if num_items_per_request > 1:
            items_array = [t * num_items_per_request for t in tps_array]
            print("\n--- Throughput Distribution (Items/sec over 1s windows) ---")
            print(f"Min:    {np.min(items_array):.2f} items/s")
            print(f"25th:   {np.percentile(items_array, 25):.2f} items/s")
            print(f"Median: {np.median(items_array):.2f} items/s")
            print(f"Average:{np.mean(items_array):.2f} items/s")
            print(f"75th:   {np.percentile(items_array, 75):.2f} items/s")
            print(f"Max:    {np.max(items_array):.2f} items/s")
    else:
        print("\n--- Throughput Distribution ---")
        print("(Test ran for < 2 seconds. Run a longer test -- e.g., more requests -- for per-second throughput percentiles)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Ray Serve BERT")
    parser.add_argument("--url", type=str, default="http://127.0.0.1:8000/", help="Target endpoint")
    parser.add_argument("--n", type=int, default=500, help="Total number of requests")
    parser.add_argument("--c", type=int, default=50, help="Concurrency (simultaneous users)")
    parser.add_argument("--batch-size", type=int, default=1, help="Number of texts per request (payload fan-out)")
    
    args = parser.parse_args()
    
    # Generate Payload based on batch size parameter
    base_text = "The quick brown fox jumps over the lazy dog. This is just a test sentence for embeddings."
    
    if args.batch_size == 1:
        payload = {"text": base_text}
    else:
        payload = {"texts": [base_text for _ in range(args.batch_size)]}
        
    print(f"Warming up... Benchmarking {args.url}")
    print(f"Total requests: {args.n}, Concurrency: {args.c}, Batch Size (per request): {args.batch_size}")
    
    # Run the event loop
    results = asyncio.run(run_benchmark(args.url, args.n, args.c, payload))
    print_stats(results, args.batch_size)
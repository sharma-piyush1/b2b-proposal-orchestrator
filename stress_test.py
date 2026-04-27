import asyncio
import aiohttp
import time

async def trigger_workflow(session, url, thread_index):
    payload = {
        "rfp_text": f"We need a scalable multi-agent system on AWS. Thread {thread_index}.",
        "thread_id": f"stress_test_{thread_index}"
    }
    
    start_time = time.time()
    try:
        async with session.post(url, json=payload) as response:
            status = response.status
            await response.text() 
            latency = time.time() - start_time
            return status, latency
    except Exception as e:
        return str(e), time.time() - start_time

async def main():
    url = "http://localhost:8000/generate-proposal"
    concurrent_users = 10 
    
    print(f"Initiating stress test: {concurrent_users} concurrent requests...")
    global_start = time.time()
    
    async with aiohttp.ClientSession() as session:
        tasks = [trigger_workflow(session, url, i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks)
        
    global_time = time.time() - global_start
    
    successes = [r for r in results if r[0] == 200]
    failures = [r for r in results if r[0] != 200]
    
    avg_latency = sum(r[1] for r in successes) / len(successes) if successes else 0
    
    print("\nTest Complete.")
    print("-" * 20)
    print(f"Total Execution Time:  {global_time:.2f} seconds")
    print(f"Successful Requests:   {len(successes)}")
    print(f"Failed Requests:       {len(failures)}")
    print(f"Average Node Latency:  {avg_latency:.2f} seconds")
    
    if failures:
        print("\nFailure Sample:")
        print(failures[0])

if __name__ == "__main__":
    asyncio.run(main())
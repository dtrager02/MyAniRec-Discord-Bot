import aiohttp
import asyncio
import ray
import json
from time import perf_counter as pc
async def fetch(session, url,sleep):
    # await asyncio.sleep(sleep)
    # print("in")
    return await session.post(url, json={"array": [29803,35790,30831]})
async def fetchhandle(session, handle,sleep):
    # await asyncio.sleep(sleep)
    # print("in")
    result = ray.get(handle.calldirect.remote(ids= [29803,35790,30831]))
    return result
async def main(handle):
    async with aiohttp.ClientSession(trust_env = True) as session:
        # tasks = [fetchhandle(session, handle,i/1000.0) for i in range(10000)]
        tasks = [fetch(session, "http://localhost:8000",i/10.0) for i in range(10)]
        resps = await asyncio.gather(*tasks)
        text = await resps[0].text()
        print(text)
        jsons_ = [resp.json() for resp in resps]
        jsons = await asyncio.gather(*jsons_)
        print(jsons[0],type(jsons[0]))
        await session.close()
#policy = asyncio.WindowsSelectorEventLoopPolicy()
#asyncio.set_event_loop_policy(policy)
loop = asyncio.get_event_loop()
start = pc()
loop.run_until_complete(main(None))
print(pc()-start)

#regular async 1000 calls takes 2.7s
#12 replicas 10000 calls takes 11-13s
#12 replicas 1000 calls takes 1.3s

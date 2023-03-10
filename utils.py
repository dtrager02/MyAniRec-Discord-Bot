import aiohttp
import asyncio
import torch

# response = requests.get('https://myanimelist.net/search/prefix.json', params=params, cookies=cookies, headers=headers)
async def fetch(session,q):
    params = {
    'type': 'anime',
    'keyword': q,
    'v': '1',
    }
    async with session.get('https://myanimelist.net/search/prefix.json',params=params) as response:
        # print("Status:", response.status)
        # print("Content-type:", response.headers['content-type'])
        data = await response.json()
        # print(data)
        data = [(data['name'],data['id']) for data in data['categories'][0]['items']]
        # print("Body:", str(data), "...")
        return data
    
def asint(l):
    return [int(i) for i in l]
    
async def formatlist(data,start=1):
    out = str("\n".join(["**{}:** {}".format(i,s[0]) for i,s in enumerate(data, start=start)]))
    return out
def formatlist2(data,start=1):
    out = str("\n".join(["**{}:** {}".format(i,s) for i,s in enumerate(data, start=start)]))
    return out
async def get_ranking(data,converter,seen_items):
    seen = converter.loc[converter.index.isin(seen_items),"train_id"].values
    data[0,seen] = -torch.inf
    out_sorted = torch.argsort(data,dim=1,descending=True)
    out_sorted_converted = converter.reset_index().set_index("train_id").loc[out_sorted[0,:400].tolist(),"item_id"].values
    return out_sorted_converted

async def main(session):
    a = await fetch(session,"haj")
    b = await formatlist(a)
    print(b)
    await session.close()
    
if __name__ == '__main__':
    session = aiohttp.ClientSession()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(session))
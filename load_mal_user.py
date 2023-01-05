import torch
import aiohttp
import asyncio
import numpy as np
import pandas as pd
async def fetch_user(session:aiohttp.ClientSession,user:str):
    headers = {
    'authority': 'myanimelist.net'
    }
    
    headers['Referer'] = f'https://myanimelist.net/animelist/{user.strip()}'
    a = []
    offset = 0
    r = await session.get(f"https://myanimelist.net/animelist/{user.strip()}/load.json?offset={offset}&status=7",headers=headers)  
    status = r.status
    try:
        res_json = await r.json()
        if "errors" not in res_json: 
            a.extend(res_json)
            offset = len(a)
        while len(a)%300==0 and len(a) and len(res_json):
            # time.sleep(random.random()/10)
            r = await session.get(f"https://myanimelist.net/animelist/{user.strip()}/load.json?offset={offset}&status=7",headers=headers)  
            status = r.status
            res_json = await r.json()
            a.extend(res_json)
            offset += len(a)
        return {'status':status,'content':a,'user':user}
    except Exception as e:
        print(e.with_traceback())
        return {'status':status,'content':None,'user':user}

#SUBJECT TO CHANGE    
async def generate_user_tensor(items,item_map):
    out = torch.zeros((1,item_map.shape[0]))
    # res = np.array([[s['anime_id'],s['score']] for s in res['content'] if s['status'] == 2])
    # res = res[res[:,1]>=np.median(res[:,1]),0]
    res = item_map.loc[item_map.index.isin(items),"train_id"].values
    out[0,res] = 1
    return out



def get_liked_anime(res:dict):
    res = np.array([[s['anime_id'],s['score']] for s in res['content'] if s['status'] == 2])
    if len(res) == 0:
        return []
    res = res[res[:,1]>=np.median(res[:,1]),0].tolist()
    return res

async def get_anime_ids(res:dict):
    return [s['anime_id'] for s in res['content'] if s['status'] == 2]
async def main(session):
    a = await fetch_user(session,"lovinvader")
    print(a['status'],len(a['content']))
    b = await generate_user_tensor(a,10175,item_map)
    print(b)
    await session.close()


if __name__ == "__main__":
    session = aiohttp.ClientSession()
    item_map = pd.read_csv("item_map.csv").set_index("item_id")
    # out = generate_user_tensor("EscanorPie",10175,item_map)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(session))
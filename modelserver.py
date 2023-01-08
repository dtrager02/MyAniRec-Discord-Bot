import torch
import starlette.requests
import requests
from ray import serve
import ray
from ray.serve.drivers import DAGDriver
import pandas as pd
from time import perf_counter as pc
from utils import *
from load_mal_user import *
import sys
import logging

async def json_to_arr(req: starlette.requests.Request):
    a = await req.json()
    return a['array']

# @serve.deployment
# class Model2:
#     def __call__(self, arr: list):
#         return sum(arr)

logger = logging.getLogger("ray.serve")

@serve.deployment(ray_actor_options={"num_cpus": 1},num_replicas=12,max_concurrent_queries=150)
class Model:
    def __init__(self,model_path,preprocessor) -> None:
        sys.path.insert(0, './models')
        logger.info("Hello world!")
        logger.setLevel(logging.ERROR)
        self.model = torch.load(model_path,map_location=torch.device('cpu'))
        self.model.eval()    
        self.preprocessor = preprocessor
    async def __call__(self, req: starlette.requests.Request):
        ids = await json_to_arr(req)
        input = self.preprocessor.generate_user_tensor(ids)
        #print(input.shape,"abcd",flush=True)
        output,_,_ = self.model(torch.from_numpy(input))
        ranks =self.preprocessor.get_ranking(output,ids)
        #print(pc()-start,"time taken total",flush=True)
        return {"ranks":ranks}
    # async def calldirect(self, ids):
    #     input = self.preprocessor.generate_user_tensor(ids)
    #     #print(input.shape,"abcd",flush=True)
    #     output,_,_ = self.model(torch.from_numpy(input))
    #     ranks =self.preprocessor.get_ranking(output,ids)
    #     #print(pc()-start,"time taken total",flush=True)
    #     return ranks
    
# @serve.deployment(ray_actor_options={"num_cpus": 1},num)
class Preprocessor:
    def __init__(self,item_map_path) -> None:
        self.item_map = pd.read_csv(item_map_path).set_index("item_id")
    def get_ranking(self,data2,seen_items):
        # start = pc()
        seen = self.item_map.loc[self.item_map.index.isin(seen_items),"train_id"].values
        data = data2.detach().clone()
        data[0,seen] = -torch.inf
        out_sorted = torch.argsort(data,dim=1,descending=True)
        out_sorted_converted = self.item_map.reset_index().set_index("train_id").loc[out_sorted[0,:400].tolist(),"item_id"].values
        #print(pc()-start,"time taken rank",flush=True)
        return out_sorted_converted
    

    def generate_user_tensor(self,items):
        start = pc()
        out = torch.zeros((1,self.item_map.shape[0]))
        res = self.item_map.loc[self.item_map.index.isin(items),"train_id"].values
        out[0,res] = 1
        return out.numpy()


#benchmark for original methods
# async def main(model,ids,item_map):
#     a = await generate_user_tensor(ids,item_map=item_map)
#     output,_,_ = model(a)
#     # #print("hi")
#     ranks = await get_ranking(output,item_map,ids)
#     return ranks

# if __name__ == "__main__":

p = Preprocessor("item_map.csv")
m = Model.bind("models/multvae.pt",p)
# graph = DAGDriver.bind(m, http_adapter=json_to_arr)
handle = serve.run(m)
loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.sleep(2**31))
####################HTTP RAY BENCH
# policy = asyncio.WindowsSelectorEventLoopPolicy()
# asyncio.set_event_loop_policy(policy)
# loop.run_until_complete(benchmark.main(handle))
# start = pc()

# print(pc()-start,"time taken",flush=True)
####################HTTP NO RAY JUST PYTHON BENCH
    # sys.path.insert(0, './models')
    # mod = torch.load("models/multvae.pt",map_location=torch.device('cpu'))
    # im = pd.read_csv("./item_map.csv").set_index("item_id")
    # start = pc()
    # loop.run_until_complete(asyncio.gather(*[main(mod,[29803,35790,30831],im) for _ in range(1000)]))
    # print(pc()-start,"time taken",flush=True)
    #print(resp.json())
import torch
import multiprocessing
from time import perf_counter
available_gpus = [torch.cuda.device(i) for i in range(torch.cuda.device_count())]
print(available_gpus)
print(multiprocessing.cpu_count())
print(torch.__config__.show())
# a = torch.rand(2**15,2**9)
# b = torch.rand(2**9,2**12)
# #mult
# start = perf_counter()
# y = a @ b
# end = perf_counter()
# print(end-start)
# #sum
# start = perf_counter()
# y = a + a.log()
# end = perf_counter()
# print(end-start)
# #agg
# start = perf_counter()
# y = a.log().sum()
# end = perf_counter()
# print(end-start)

# a = a.half().to("cuda:0")
# b = b.half().to("cuda:0")
# start = torch.cuda.Event(enable_timing=True)
# end = torch.cuda.Event(enable_timing=True)

# start.record()
# z = a @ b
# end.record()

# # Waits for everything to finish running
# torch.cuda.synchronize()

# print(start.elapsed_time(end))
# #sum
# start = torch.cuda.Event(enable_timing=True)
# end = torch.cuda.Event(enable_timing=True)

# start.record()
# z = a + a.log()
# end.record()

# # Waits for everything to finish running
# torch.cuda.synchronize()

# print(start.elapsed_time(end))
# #agg
# start = torch.cuda.Event(enable_timing=True)
# end = torch.cuda.Event(enable_timing=True)

# start.record()
# z = a.log().sum()
# end.record()

# # Waits for everything to finish running
# torch.cuda.synchronize()

# print(start.elapsed_time(end))

# ########################

# a = a.float().to("cuda:0")
# b = b.float().to("cuda:0")
# start = torch.cuda.Event(enable_timing=True)
# end = torch.cuda.Event(enable_timing=True)

# start.record()
# z = a @ b
# end.record()

# # Waits for everything to finish running
# torch.cuda.synchronize()

# print(start.elapsed_time(end))
# #sum
# start = torch.cuda.Event(enable_timing=True)
# end = torch.cuda.Event(enable_timing=True)

# start.record()
# z = a + a.log()
# end.record()

# # Waits for everything to finish running
# torch.cuda.synchronize()

# print(start.elapsed_time(end))
# #agg
# start = torch.cuda.Event(enable_timing=True)
# end = torch.cuda.Event(enable_timing=True)

# start.record()
# z = a.log().sum()
# end.record()

# # Waits for everything to finish running
# torch.cuda.synchronize()

# print(start.elapsed_time(end))



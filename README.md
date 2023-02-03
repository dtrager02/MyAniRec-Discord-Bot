# MyAniRec-Discord-Bot

Add the bot: [link](https://discord.com/api/oauth2/authorize?client_id=1058523711570980865&permissions=534723815520&redirect_uri=https%3A%2F%2Fwww.reddit.com%2Fr%2FPurdue%2F&response_type=code&scope=bot%20messages.read%20applications.commands)

## Main Stack
Python, Redis, sqlite3, Pandas, Pytorch, discordpy, Ray Serve, asyncio, aiohttp

## Instructions on a Linux,slurm system

1. Git clone this repository
2. scp token and existing Redis dump files to server
3. Install Redis from source
4. Copy dump.rdb to redis-stable
5. Create this job file if using one node
```bash
  ray start --head --port=6400
  serve deploy server.yaml
  # can run python3 benchmark.py to ensure server is working
  #set redis config to daeomonize and save more frequently
  redis-stable/src/redis-server redis-stable/redis.conf
  nohup python3 main.py
```
## TODO
- [ ] Write the official documentation, blog
- [x] Clean up code
- [x] Optimize Redis schema
- [x] Add Redis to sql{ite?} backup system
- [ ] Figure out way to use a global aiohttp.Clientsession 
- [x] create proper install and run scripts
- [ ] Reformat Pytorch model architecture to speed up torchscript, and enable using intel MKL
- [x] Add cache for .rec complete if nothing has changed since previous
- [x] Add structured logging?
- [x] Figure out slash commands

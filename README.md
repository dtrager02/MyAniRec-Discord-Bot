# MyAniRec-Discord-Bot

Evidently, a lot of the code is very messy. This is temporary. I was making most of this in a rush over winter break and was getting irritated debugging all the new frameworks I used. 

## Main Stack
Python, Redis, sqlite3, Pandas, Pytorch, discordpy, Ray Serve, asyncio, aiohttp

## Instructions on a Linux,slurm system

1. Git clone this repository
2. scp token and existing Redis dump files to server
3. Install Redis from source
4. Copy dump.rdb to 
5. Create this job file if using one node
```bash
  "firstName": "John",
  "lastName": "Smith",
  "age": 25
}
```
6. module load slurm
7. sbtach jobfile
## TODO
- [ ] Write the official documentation, blog
- [ ] Clean up code
- [ ] Optimize Redis schema
- [ ] Add Redis to sql{ite?} backup system
- [ ] Figure out way to use a global aiohttp.Clientsession 
- [ ] create proper install and run scripts
- [ ] Reformat Pytorch model architecture to speed up torchscript, and enable using intel MKL
- [ ] Add cache for .rec complete if nothing has changed since previous
- [ ] Add structured logging?
- [ ] Figure out slash commands

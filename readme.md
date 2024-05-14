
# Installation
You can install mongo db and import size charts data using the following command.
```
https://www.cherryservers.com/blog/install-mongodb-ubuntu-22-04
sudo systemctl start mongod
sudo systemctl status mongod
sudo systemctl enable mongod
mongorestore --db brand ./dump/brand
```
You can install the deps by ```pip install -r requirements.txt```
It is highly recommend that you use a virtual environment.

# Run it locally 
You can just run the server as "python server.py"
You can also run "python relay.py", that is simply a relay to a stable diffusion web UI instance that is used for face swap
You can ignore crawler.py and domain.py

You also need to add openai api key to environment varibles to make it work, you can add this to `~/.bashrc` and `source ~/.bashrc`

```
export OPENAI_API_KEY='sk-THE_ACTUAL_KEY'
```
Ask Jia for ChatGPT account if you need one

# Deployment
We deployed the backend in a VPS, think it as a linux machine that is always on 
You can ssh to that machine using the command(please ask Tianlong for password)
```ssh faishion@89.117.79.105```
After logged in, when you do 
```tmux ls```
You will see 2 tmux sessions, that are the server and relay

You can attach to these sessions and observe the logs using 
```
tmux attach-session -t faishion
```
or
```
tmux attach-session -t relay
```

That machine already have a github account configured, so you can push and pull code as you want. After you made the changes, the flask server will 
reload automatically.

We are using cloudflare tunnels to expose the services:
```
sdrelay.faishion.ai # http://localhost:5000
api.faishion.ai # http://localhost:5001
```

Note that our researcher is developing a more comprehensive model in another machine under ```tryon-advanced.tianlong.co.uk```
That is not version controlled yet and it is on another machine, ignore that for now

This backend service also use OpenAI API for size recommendation, the key is already configured on this machine. 


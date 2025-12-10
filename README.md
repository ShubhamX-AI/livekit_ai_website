### Backend installation

```
git clone https://github.com/shubhamINT/livekit_ai_website.git
cd livekit_ai_website/backend
python -m venv venv
pip install -r requirements.txt
python agent_session.py download-files
```

## Then in one terminal 
```
python server_run.py
```
Another terminal

```
python agent_session.py start
```

### For Frontend 

```
cd ../frontend
npm install
npm run dev
```


### Runnig in locally some examples
```
docker pull livekit/livekit-server
docker run -d --name livekit-server -p 7880:7880 -p 7881:7881 -p 7882:7882/udp -e LIVEKIT_KEYS="devkey: secret" livekit/livekit-server --dev --bind 0.0.0.0 --node-ip 127.0.0.1

LIVEKIT_API_KEY="devkey"
LIVEKIT_API_SECRET="secret"
LIVEKIT_URL="ws://localhost:7880"
```
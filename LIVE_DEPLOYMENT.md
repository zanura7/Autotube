# Live deployment: Cloudflare Pages + VPS

Autotube uses a split deployment:

- **Cloudflare Pages** serves the Solid/Vite web interface.
- **VPS** runs FastAPI, SQLite, FFmpeg, the schedule engine, and the long-lived RTMP process.
- **Cloudflare Tunnel** can publish the API without exposing port 8000 on the VPS.
- **Modal** is reserved for finite render jobs later. A continuous FFmpeg livestream belongs on the VPS because it needs a stable process, local media, and predictable restart behavior.

## What the live engine supports

A live job can use:

- one or many videos as a playlist;
- one or many images, each with a configurable duration;
- one or many audio files;
- original video audio, replacement music, or a mix of both;
- bars, waveform, or spectrum visualization;
- visualizer position, colors, size, opacity, and sensitivity;
- loop, shuffle, automatic retry, one-time scheduling, and daily scheduling;
- YouTube RTMP or another RTMP/RTMPS destination.

The stream key is encrypted before it is stored. The API never returns it. Runtime state and recent logs are kept in the database so the UI can recover after a page refresh.

## 1. Deploy the backend on a VPS

Requirements:

- Docker Engine with the Compose plugin;
- outbound access to the RTMP destination;
- enough CPU for real-time H.264 encoding. Start with at least 2 vCPU for 720p and measure before raising resolution or FPS.

Create the production environment:

~~~bash
cp .env.live.example .env.live
python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
~~~

Put the generated value in **AUTOTUBE_SECRET_KEY**. Keep that key stable: changing it makes stored stream keys unreadable.

Set **AUTOTUBE_CORS_ORIGINS** to the exact Pages/custom-domain origin, without a trailing slash. Then start the API:

~~~bash
docker compose -f docker-compose.live.yml up -d --build api
docker compose -f docker-compose.live.yml ps
curl http://127.0.0.1:8000/health
~~~

The host port is bound to **127.0.0.1**, so it is not directly exposed to the Internet. The container intentionally uses one Uvicorn worker because the scheduler and FFmpeg process registry currently live in the API process.

Persistent Docker volumes contain:

- **autotube_data**: SQLite database, scheduler database, and encrypted credentials;
- **autotube_uploads**: uploaded source media;
- **autotube_generations**: rendered output.

Back up all three volumes together with **.env.live**.

## 2. Publish the API with Cloudflare Tunnel

Create a remotely managed tunnel in Cloudflare and add a public hostname such as **api.example.com**. When the tunnel runs in the Compose network, use this service URL:

~~~text
http://api:8000
~~~

Copy the tunnel token into **TUNNEL_TOKEN**, then run:

~~~bash
docker compose -f docker-compose.live.yml --profile tunnel up -d
~~~

Protect both the frontend and API hostnames with a Cloudflare Access policy for the allowed users. This is a control panel that can start paid compute and publish to a YouTube channel, so it should not be public.

If you use a host-installed **cloudflared** service instead, route the hostname to **http://localhost:8000** and start only the API Compose service.

## 3. Deploy the frontend to Cloudflare Pages

Connect the GitHub repository in Workers & Pages and use:

| Setting | Value |
|---|---|
| Root directory | frontend |
| Build command | npm ci && npm run build |
| Build output directory | dist |
| Node version | 22 |

Set these production environment variables:

~~~text
VITE_API_BASE_URL=https://api.example.com
VITE_WS_BASE_URL=wss://api.example.com
~~~

The values are build-time settings. Trigger a new Pages deployment after changing them. The included **frontend/public/_redirects** keeps client-side routes working on direct navigation.

After deployment, set the final Pages/custom-domain origin in the VPS value **AUTOTUBE_CORS_ORIGINS**, then recreate the API container:

~~~bash
docker compose -f docker-compose.live.yml up -d --force-recreate api
~~~

## 4. Verify the deployed system

1. Open **/health** on the API hostname and confirm **status** is **healthy** and **ffmpeg** is **true**.
2. Upload a short video or image and an MP3 from the Live Streaming page.
3. Use a temporary/unlisted YouTube stream key.
4. Start at 720p, 30 FPS, 2500 kbps.
5. Confirm the UI changes from **starting** to **live**, logs continue updating, and YouTube receives H.264 video plus AAC audio.
6. Stop the stream from the UI and confirm FFmpeg exits and the status becomes **stopped**.
7. Restart the API during a disposable test stream and confirm an auto-restart job recovers it.

## Current production boundary

SQLite is suitable for one API instance. Before running multiple API/worker replicas, move the job state to PostgreSQL and add an atomic worker lease. Media should then move to object storage or a shared volume. The existing API contract and UI can remain in place while that worker layer changes.

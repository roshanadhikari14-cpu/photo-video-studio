# Edit Studio: photo & video request portal

A simple, mobile-friendly website where people upload photos and videos and describe the edit they want.
Each request is downloaded to your PC, edited by Claude Code into a full Instagram package (posts, stories,
collages, reels, graded photos, captions), and published back to the sender's own reference link.

Live: https://photo-video-studio-gamma.vercel.app

## How it works

```
Browser ──upload──▶ Vercel Blob (files + request.json)
   │                       ▲            │
   │  /r/<id> polls        │ results    │ new request
   ▼  /api/status          │ + status   ▼
Reference page  ◀──────────┴──── local/agent.mjs on your PC ──▶ Claude Code (edits in client-requests/<id>/)
```

| Path | What it is |
|---|---|
| `public/index.html` | Upload page: multiple photos/videos, prompt box, per-file and overall % |
| `public/r.html` | Reference link `/r/<id>`: live progress %, then a gallery (posts, stories, collages, videos, photos) with download, copy caption and a swipe viewer |
| `api/upload.js` | Issues short-lived tokens so the browser uploads straight to Vercel Blob (up to 4 GB per file, multipart) |
| `api/submit.js` | Saves the request once all files are uploaded |
| `api/status.js` | Request, latest status/progress and grouped results for the reference page |
| `local/agent.mjs` | Runs on your PC: downloads requests, runs Claude Code, publishes results and progress |
| `local/toolkit/` | Reference editing scripts Claude borrows from (grading, typography, collages, reels) |
| `start-watching.bat` | Double-click to start watching for requests |

## Setup

```bash
npm install
npx vercel link                       # link to your Vercel project
npx vercel blob create-store <name> --access public --yes
npx vercel env pull .env.local        # gives the local agent BLOB_READ_WRITE_TOKEN
npx vercel deploy --prod
```

`public/blob-client.js` is a prebuilt bundle of `@vercel/blob/client`; rebuild it with `npm run build` after upgrading the package.

## Running the agent (on your PC)

```bash
node local/agent.mjs              # watch: download new requests every minute
node local/agent.mjs list         # all requests and their status
node local/agent.mjs run <id>     # Claude edits the request, results are published
node local/agent.mjs publish <id> # publish whatever is in results/ by hand
```

Files land in `../client-requests/<date>_<name>_<id>/` (`uploads/`, `PROMPT.txt`, `results/`).
Settings live in `local/config.json` (created on first run, not committed): `requestsFolder`, `siteUrl`,
`autoRun` (hand every new request to Claude without asking; off by default because anyone with the link can
send a prompt), `checkEverySeconds`, `pythonDir`, `extraDirs`.

## Notes

- Uploaded files and results are public blobs with random, unguessable URLs; request ids are 12 random characters.
- Claude runs with a limited tool set (file read/write, ffmpeg, ffprobe, python) inside the request folder and is told
  to treat the client's prompt only as a description of the edit.
- Music in generated videos is synthesized, never copyrighted songs.

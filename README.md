# Framed

A personal image gallery. Log in, upload your pictures to a private dashboard, edit or delete them, share any single image as an unlisted link, or publish it to a public gallery that anyone can browse and like.

- **Backend** — FastAPI (Python 3.11+), SQLite, local disk storage, JWT auth
- **Frontend** — React 18 + Vite + React Router

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            # app setup, CORS, router wiring
│   │   ├── config.py          # settings from env / .env
│   │   ├── database.py        # SQLite engine + session dependency
│   │   ├── migrate.py         # additive ALTER TABLE for columns added later
│   │   ├── models.py          # User, Image, Like
│   │   ├── schemas.py         # request/response models
│   │   ├── security.py        # bcrypt hashing, JWT, get_current_user
│   │   ├── storage.py         # streamed upload to disk, type/size limits
│   │   └── routers/
│   │       ├── auth.py        # register, login, me
│   │       ├── images.py      # CRUD + share + publish (token-protected)
│   │       └── public.py      # share links, gallery feed, likes
│   ├── tests/                 # pytest suite
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api.js             # fetch wrapper, attaches Bearer token
│   │   ├── auth.jsx           # AuthProvider / useAuth
│   │   ├── App.jsx            # routes + route guards
│   │   ├── pages/             # Login, Register, Dashboard, Explore, SharedImage
│   │   └── components/        # UploadForm, ImageCard, LikeButton
│   ├── eslint.config.js
│   ├── Dockerfile
│   ├── nginx.conf
│   └── .env.example
├── docker-compose.yml
├── prd.txt                    # requirements specification
└── README.md
```

## How auth works

1. `POST /auth/register` or `/auth/login` returns a **JWT** (HS256, 60 min by default). Passwords are hashed with bcrypt and never stored or returned.
2. The frontend keeps the token in `localStorage` and sends it as `Authorization: Bearer <token>` on every request.
3. Every `/images/*` endpoint depends on `get_current_user`, which decodes the token and loads the user — no token or a bad/expired one gives **401**.
4. Queries are always filtered by `owner_id`, so another logged-in user asking for your image gets **404**, not someone else's picture.
5. On a 401 the frontend clears the token and bounces you back to `/login`.

Protected images are never exposed by URL alone: the dashboard fetches each file with the auth header and renders it from a blob URL. The only unauthenticated way to see an image is an explicit share link.

## Sharing vs. publishing

These are two different things, and the distinction is the point:

| | Share | Publish |
|---|---|---|
| Who can reach it | anyone with the link | anyone at all |
| Where it appears | nowhere — **unlisted** | listed in `/explore` |
| Column | `share_token` | `is_public` |

- **Share** mints a 32-byte URL-safe random token. The link is `/s/<token>`. Anyone with it sees **that one image** — no login, no access to the rest of your gallery. The response returns only title, description, content type, and like count.
- **Unshare** sets the token back to `NULL`, and the old link immediately 404s. Re-sharing mints a **new** token, so a leaked link stays dead.
- **Publish** lists the photo in the public gallery. It mints a share token if the photo doesn't have one, since the gallery serves image bytes through that token.
- **Unpublish** removes it from the gallery but *leaves the unlisted link working*.
- Revoking the link necessarily unpublishes, because the gallery has no other way to address the file.

Sharing never publishes. A link you sent to one person stays out of the public gallery unless you explicitly publish it.

## The public gallery

`/explore` is readable logged out and lists published photos, newest first.

- **Likes require an account.** That gets a unique `(image_id, user_id)` constraint, which makes double-liking idempotent, makes un-liking possible, and keeps the count meaningful. A logged-out visitor who clicks like is sent to `/login`.
- The feed sends your token when you have one, so the server can mark which photos you already liked (`liked_by_me`). A stale or invalid token degrades to anonymous rather than erroring.
- **Pagination is keyset, not `OFFSET`.** The cursor is an opaque base64 of `(published_at, id)`. With `OFFSET`, a photo published while you're scrolling shifts every subsequent page, so you'd see duplicates and miss others. The frontend loads the next page from an `IntersectionObserver` with a 400px margin, so it arrives before you reach the bottom.

## API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/register` | – | Create an account, returns a token |
| POST | `/auth/login` | – | Log in, returns a token |
| GET | `/auth/me` | ✔ | Current user |
| GET | `/images` | ✔ | List my images (newest first) |
| POST | `/images` | ✔ | Upload (multipart: `file`, `title`, `description`) |
| GET | `/images/{id}` | ✔ | Image metadata |
| GET | `/images/{id}/file` | ✔ | Image bytes |
| PUT | `/images/{id}` | ✔ | Update title/description and/or replace file |
| DELETE | `/images/{id}` | ✔ | Delete image + file on disk |
| POST | `/images/{id}/share` | ✔ | Create (or return existing) share token |
| DELETE | `/images/{id}/share` | ✔ | Revoke share link (also unpublishes) |
| POST | `/images/{id}/publish` | ✔ | List in the public gallery (mints a token if needed) |
| DELETE | `/images/{id}/publish` | ✔ | Delist, keeping the unlisted link |
| GET | `/public/feed` | optional | Published photos, newest first — `?limit=1..50&cursor=` |
| GET | `/public/{token}` | optional | Shared image metadata |
| GET | `/public/{token}/file` | – | Shared image bytes |
| POST | `/public/{token}/like` | ✔ | Like a photo (idempotent) |
| DELETE | `/public/{token}/like` | ✔ | Remove your like |
| GET | `/health` | – | Liveness check |

"optional" means the endpoint works logged out, but sends back a little more when a token is present — `liked_by_me` on the feed and on a shared photo.

Uploads are limited to `image/jpeg`, `image/png`, `image/gif`, `image/webp` and 10 MB, enforced server-side while streaming to disk.

`/public/feed` returns `{ items, next_cursor }`. Pass `next_cursor` back as `?cursor=` for the following page; `null` means the end.

## Frontend routes

| Route | Access | Screen |
|---|---|---|
| `/login` | guest | Login form |
| `/register` | guest | Sign-up form |
| `/dashboard` | **protected** | Upload, grid, edit, delete, share, publish |
| `/explore` | public | Published photos, infinite scroll, likes |
| `/s/:token` | public | Single shared image, with like |

`/` redirects to `/dashboard`; unauthenticated visits redirect to `/login`.

---

## Running it

### Option 1 — Docker (both services at once)

Requires Docker Desktop.

```bash
# from the repo root
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

Open http://localhost:3000, sign up, and you're on the dashboard.

Other useful commands:

```bash
docker compose up -d --build      # run in the background
docker compose logs -f backend    # tail backend logs
docker compose ps                 # what's running
docker compose down               # stop (keeps your images and DB)
docker compose down -v            # stop AND wipe the DB + uploaded files
docker compose build --no-cache   # force a clean rebuild
```

The SQLite file and uploads live in named volumes (`gallery-data`, `gallery-uploads`), so they survive `down` and rebuilds — only `down -v` deletes them.

> The frontend's API URL is baked in at build time by Vite. If you serve the backend somewhere other than `http://localhost:8000`, change `VITE_API_URL` under `frontend.build.args` in `docker-compose.yml` and rebuild, and add the frontend's origin to `CORS_ORIGINS` on the backend.

#### Building the images individually

```bash
docker build -t gallery-backend ./backend
docker run -p 8000:8000 -v gallery-data:/app/data -v gallery-uploads:/app/uploads gallery-backend

docker build -t gallery-frontend --build-arg VITE_API_URL=http://localhost:8000 ./frontend
docker run -p 3000:80 gallery-frontend
```

### Option 2 — Local dev (hot reload)

Run these in **two terminals**.

**Terminal 1 — backend**

```bash
cd backend
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env          # Windows;  cp .env.example .env  on macOS/Linux
uvicorn app.main:app --reload --port 8000
```

→ API on http://localhost:8000, docs on http://localhost:8000/docs. The SQLite file (`gallery.db`) and the `uploads/` folder are created automatically on first run.

**Terminal 2 — frontend**

```bash
cd frontend
npm install
copy .env.example .env          # Windows;  cp .env.example .env  on macOS/Linux
npm run dev
```

→ App on http://localhost:5173.

Other frontend commands:

```bash
npm run build      # production build into dist/
npm run preview    # serve the production build locally
npm run lint       # ESLint (flat config, React + hooks rules)
npm run lint:fix   # ESLint with autofix
```

### Tests

```bash
cd backend
.venv\Scripts\activate      # source .venv/bin/activate on macOS/Linux
pip install pytest httpx
pytest
```

Tests run against a temporary database and upload directory, so they never touch your real data.

### First run

1. Go to the app (http://localhost:3000 for Docker, http://localhost:5173 for local dev).
2. **Sign up** with an email and a password of at least 8 characters.
3. You land on the dashboard — pick a file, give it a title, hit **Upload**.
4. **Edit** renames or replaces the picture, **Delete** removes it.
5. **Share** gives you an unlisted link to copy and send to one person.
6. **Publish** puts the photo in the public gallery at `/explore`, where anyone can see it and logged-in visitors can like it.

### Resetting the data

```bash
# Docker
docker compose down -v

# Local dev
rm backend/gallery.db && rm -rf backend/uploads    # PowerShell: Remove-Item
```

## Configuration

**backend/.env** (see `.env.example`)

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | `change-me-in-production` | **Change this.** Signs the JWTs; changing it logs everyone out. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |
| `DATABASE_URL` | `sqlite:///./gallery.db` | Swap for a Postgres URL later |
| `UPLOAD_DIR` | `./uploads` | Where image files are written |
| `MAX_UPLOAD_BYTES` | `10485760` | 10 MB |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated browser origins |

**frontend/.env**

| Variable | Default | Notes |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Read at build time, not runtime |

## Notes and next steps

- Tables are created on boot via `create_all`, which builds missing *tables* but never alters existing ones. `app/migrate.py` adds columns that appeared after a database was first created, so upgrading in place doesn't lose data. Move to Alembic once changes stop being purely additive.
- Likes are tied to accounts on purpose. Anonymous liking would need a spoofable visitor id and would make un-liking unreliable.
- SQLite + local disk is the starting point by design; moving to Postgres + S3 is a config and storage-layer change, not an API change.
- The token lives in `localStorage`, which is simple but readable by any script on the page. For a hardened deployment, move to an httpOnly refresh cookie.
- Generate a real secret before deploying: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

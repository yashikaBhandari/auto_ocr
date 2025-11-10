# AutoOCR Deployment Guide

## Quick Deploy Options

### Option 1: Render (Recommended - FREE)

#### Step 1: Push Code to GitHub
Your code is already on GitHub at: https://github.com/yashikaBhandari/auto_ocr.git

#### Step 2: Deploy on Render
1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Click **"New +"** → **"Blueprint"**
4. Connect your repository: `yashikaBhandari/auto_ocr`
5. Render will auto-detect `render.yaml` and deploy!

**Your app will be live at:** `https://autoocr-backend.onrender.com`

#### Frontend Deployment:
1. Go to Render Dashboard
2. Click **"New +"** → **"Static Site"**
3. Connect repository
4. Set build settings:
   - **Build Command:** `cd autoocr/frontend/react-app && npm install && npm run build`
   - **Publish Directory:** `autoocr/frontend/react-app/dist`

---

### Option 2: Railway (FREE $5 credit/month)

#### Already configured! Just:
1. Go to [railway.app](https://railway.app)
2. Sign in with GitHub
3. Click **"New Project"** → **"Deploy from GitHub repo"**
4. Select `yashikaBhandari/auto_ocr`
5. Railway will use `railway.json` config automatically

**Done!** Your backend will be live.

---

### Option 3: Vercel (Frontend) + Render (Backend)

#### Frontend on Vercel:
```bash
cd autoocr/frontend/react-app
npm install -g vercel
vercel
```

Follow prompts and it's live!

#### Backend on Render:
Use Option 1 steps above.

---

## Environment Variables

For production, set these on your platform:

```
PYTHONUNBUFFERED=1
PORT=8000
```

---

## Testing Your Deployment

Once deployed, test with:
```bash
# Health check
curl https://your-app.onrender.com/health

# API docs
Open: https://your-app.onrender.com/docs
```

---

## CORS Configuration

If frontend and backend are on different domains, update `autoocr/api/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Cost

- **Render Free Tier:** 750 hours/month (enough for 1 service 24/7)
- **Railway:** $5 free credit/month
- **Vercel:** Unlimited for personal projects

---

**Choose Render for easiest setup!** 🚀

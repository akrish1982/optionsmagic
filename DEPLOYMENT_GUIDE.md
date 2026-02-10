# OptionsMagic Frontend - Deployment Guide

**Created by:** Spider 🕷️  
**Date:** February 10, 2026  
**Status:** ✅ Complete - Ready for Deployment

---

## 🎯 What Was Done (Priority 1)

### ✅ 1. Extracted Frontend from Worker
**Before:** HTML was embedded inline in `api/worker.js` (hard to maintain)  
**After:** Clean separation:
```
frontend/
├── src/worker.js          # API backend only (no HTML)
├── public/index.html      # Frontend UI (complete with Bid/Ask/Volume)
└── wrangler.toml          # Deployment configuration
```

### ✅ 2. Added Missing Columns
Updated HTML to include:
- **Bid/Ask prices** - Show option pricing spread
- **Volume** - Trading volume for liquidity assessment

Both columns appear in:
- Grouped view (by ticker)
- Flat view (paginated table)

### ✅ 3. Created wrangler.toml
Proper Cloudflare Workers configuration:
- Production, staging, and development environments
- Static asset serving for HTML/CSS/JS
- Environment variable management
- Ready for custom domain routing

### ✅ 4. Set Up CI/CD Pipeline
GitHub Actions workflow (`.github/workflows/deploy-frontend.yml`):
- **On Pull Request:** Auto-deploy to staging
- **On Merge to Main:** Auto-deploy to production
- Automatic secret management
- Deployment status comments on PRs

---

## 🚀 How to Deploy

### Option 1: Automatic Deployment (Recommended)

**Setup GitHub Secrets (One-time):**

1. Go to your GitHub repo: https://github.com/akrish1982/optionsmagic
2. Navigate to: **Settings → Secrets and variables → Actions → New repository secret**
3. Add these 4 secrets:

| Secret Name | Where to Get It | Example |
|-------------|-----------------|---------|
| `CLOUDFLARE_API_TOKEN` | https://dash.cloudflare.com/profile/api-tokens<br/>Create Token → "Edit Cloudflare Workers" template | `abc123...` |
| `CLOUDFLARE_ACCOUNT_ID` | https://dash.cloudflare.com/<br/>Copy the Account ID from the URL | `32bee28132abb6da...` |
| `SUPABASE_URL` | Supabase Dashboard → Project Settings → API | `https://xxxxx.supabase.co` |
| `SUPABASE_KEY` | Supabase Dashboard → Project Settings → API → anon/public key | `eyJhbG...` |

**Deploy:**
```bash
# From your local machine
cd /home/openclaw/.openclaw/workspace/optionsmagic
git add frontend/ .github/
git commit -m "feat: extract frontend and setup CI/CD"
git push origin main
```

✅ GitHub Actions will automatically deploy to production!

---

### Option 2: Manual Deployment

If you want to deploy manually (without GitHub Actions):

```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic/frontend

# 1. Create .dev.vars for local testing
cp .dev.vars.template .dev.vars
nano .dev.vars  # Add your Supabase credentials

# 2. Test locally
npm run dev
# Visit http://localhost:8787

# 3. Set production secrets
npx wrangler secret put SUPABASE_URL --env production
npx wrangler secret put SUPABASE_KEY --env production

# 4. Deploy to production
npm run deploy:production
```

---

## 🔧 Local Development

**Start local dev server:**
```bash
cd frontend
npm run dev
```

**Test the API:**
```bash
curl "http://localhost:8787/api/options?expiration_window=45"
curl "http://localhost:8787/api/expirations"
```

**View frontend:**
Open http://localhost:8787 in your browser

---

## 📊 Current vs New Structure

### Before (api/worker.js)
```javascript
const HTML_PAGE = `<!DOCTYPE html>...`; // 500+ lines inline!

export default {
  async fetch(request, env, ctx) {
    if (path === "/") {
      return new Response(HTML_PAGE, {...}); // Messy!
    }
    // API logic mixed with HTML...
  }
}
```

### After (frontend/src/worker.js)
```javascript
// Clean API-only code
export default {
  async fetch(request, env, ctx) {
    if (path === "/api/options") return handleOptionsRequest(url, env);
    if (path === "/api/expirations") return handleExpirationsRequest(env);
    // HTML served automatically from public/index.html via wrangler.toml
  }
}
```

✅ **Benefits:**
- Easier to maintain (separate files)
- Version control for HTML changes
- Automated deployments
- Staging environment for testing
- No more manual copy-paste in dashboard

---

## 🌐 Deployment URLs

After deployment, your frontend will be available at:

**Current (manual deployment):**
- https://royal-grass-05ca.akrish1982.workers.dev

**New (automated deployment):**
- **Production:** https://optionsmagic-api-production.akrish1982.workers.dev
- **Staging:** https://optionsmagic-api-staging.akrish1982.workers.dev

**Future (when you connect domain in Priority 2):**
- https://options-magic.com
- https://www.options-magic.com

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] Frontend loads at worker URL
- [ ] `/api/options` returns data
- [ ] Bid/Ask column shows in table
- [ ] Volume column shows in table
- [ ] Filters work (symbol, expiration window, long-bias)
- [ ] Grouped and Flat views toggle
- [ ] Sorting works on columns
- [ ] Bollinger Band indicators display
- [ ] Refresh button fetches new data

**Test commands:**
```bash
# Test API endpoint
curl "https://your-worker.workers.dev/api/options?expiration_window=30&long_bias=true" | jq .

# Check if bid/ask/volume are in response
curl "https://your-worker.workers.dev/api/options" | jq '.data[0] | {bid, ask, volume}'
```

---

## 🐛 Troubleshooting

### Issue: "Missing SUPABASE_URL or SUPABASE_KEY"

**Solution:**
```bash
# For production deployment
cd frontend
npx wrangler secret put SUPABASE_URL --env production
npx wrangler secret put SUPABASE_KEY --env production
```

### Issue: "404 Not Found" on deployed site

**Solution:** Check wrangler.toml has `[site]` config:
```toml
[site]
bucket = "./public"
```

### Issue: GitHub Actions failing

**Solution:** Verify all 4 GitHub Secrets are set correctly:
- CLOUDFLARE_API_TOKEN
- CLOUDFLARE_ACCOUNT_ID
- SUPABASE_URL
- SUPABASE_KEY

---

## 📋 Next Steps (Priority 2 - Backlog)

**Domain Connection:**
1. In Cloudflare Dashboard: Workers → optionsmagic-api-production → Triggers
2. Add Custom Domain: `options-magic.com`
3. Add Custom Domain: `www.options-magic.com`
4. Update DNS automatically (Cloudflare handles this)

**Cloudflare Access (Authentication):**
1. Go to https://one.dash.cloudflare.com
2. Access → Applications → Add application
3. Protect options-magic.com with email auth

---

## 📞 Questions?

**For Spider:**
- Frontend architecture questions
- Deployment issues
- CI/CD pipeline problems

**For Max:**
- Backend/database integration
- Supabase schema issues
- Python data pipeline

---

## 🎉 Summary

**What's Ready:**
- ✅ Clean frontend code structure
- ✅ Bid/Ask and Volume columns added
- ✅ Automated CI/CD pipeline
- ✅ Staging + Production environments
- ✅ Version-controlled deployments

**What's Next:**
- 🔲 Connect options-magic.com domain (Priority 2)
- 🔲 Add authentication (Priority 2)
- 🔲 Modernize dependencies (Priority 3)

**Status:** 🟢 **Ready to Deploy**

Deploy with confidence! 🕷️

---

**Last Updated:** February 10, 2026  
**Author:** Spider (OpenClaw Agent)

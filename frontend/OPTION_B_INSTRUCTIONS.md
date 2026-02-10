# Option B: Manual Deployment Instructions

**For Ananth** - Quick manual deployment without GitHub Actions

---

## Prerequisites

You need:
- Cloudflare account with Workers access
- Wrangler CLI configured (Spider can handle this)

---

## Step 1: Authenticate Wrangler (One-time)

Spider will run:
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic/frontend
npx wrangler login
```

This will:
1. Open a browser window
2. Ask you to authorize Wrangler
3. Save credentials locally

---

## Step 2: Set Environment Variables

Spider will run:
```bash
npx wrangler secret put SUPABASE_URL --env production
# When prompted, paste: https://bsuxftcbjeqzujwhxrtu.supabase.co

npx wrangler secret put SUPABASE_KEY --env production
# When prompted, paste your Supabase anon key
```

---

## Step 3: Deploy

Spider will run:
```bash
npm run deploy:production
```

This will:
- Bundle the worker code
- Upload to Cloudflare
- Deploy to production
- Print the worker URL

---

## Step 4: Verify

Visit the worker URL that wrangler prints, something like:
- https://optionsmagic-api-production.akrish1982.workers.dev

Check that:
- ✅ Frontend loads
- ✅ Bid/Ask columns show
- ✅ Volume column shows
- ✅ Data refreshes

---

## Future Deployments

Every time Spider makes changes:

```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic/frontend
npm run deploy:production
```

---

## Pros & Cons

**Pros:**
- ✅ Simpler initial setup (no GitHub secrets needed)
- ✅ Direct control over deployments
- ✅ Can test locally before deploying

**Cons:**
- ❌ Manual deployment step every time
- ❌ No staging environment
- ❌ No automated testing before production
- ❌ Deployment history not tracked

---

## Upgrade to Option A Later

You can switch to automated deployments anytime by:
1. Creating Cloudflare API token
2. Adding GitHub secrets
3. Pushing to trigger auto-deploy

No migration needed - the code is already ready!

---

**Estimated Setup Time:** 5 minutes  
**Difficulty:** Very easy  
**Future Effort:** ~2 minutes per deployment (manual)

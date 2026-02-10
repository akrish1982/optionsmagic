# ⚡ Quick Start - 5 Minutes to Deploy

## 🚀 Fastest Path to Production

### Step 1: Add GitHub Secrets (2 minutes)

1. Go to: https://github.com/akrish1982/optionsmagic/settings/secrets/actions
2. Click **New repository secret** for each:

**CLOUDFLARE_API_TOKEN:**
- Visit: https://dash.cloudflare.com/profile/api-tokens
- Click "Create Token"
- Use template: "Edit Cloudflare Workers"
- Copy the token → Paste in GitHub

**CLOUDFLARE_ACCOUNT_ID:**
- Visit: https://dash.cloudflare.com
- Copy the Account ID from the URL (32-character string)
- Example: `32bee28132abb6da65fdebd61dc7e22a`

**SUPABASE_URL:**
- Visit your Supabase dashboard
- Settings → API → Project URL
- Example: `https://bsuxftcbjeqzujwhxrtu.supabase.co`

**SUPABASE_KEY:**
- Same page → anon/public key
- Starts with `eyJhbG...`

### Step 2: Deploy (1 minute)

```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic
git push origin main
```

✅ **Done!** GitHub Actions will deploy automatically.

### Step 3: Verify (2 minutes)

1. Go to: https://github.com/akrish1982/optionsmagic/actions
2. Watch the deployment progress
3. When green ✅, visit your Worker URL
4. Check that Bid/Ask and Volume columns appear

---

## 🧪 Test Locally First (Optional)

```bash
cd frontend
cp .dev.vars.template .dev.vars
# Edit .dev.vars with your Supabase credentials
npm run dev
# Visit http://localhost:8787
```

---

## ✅ Success Checklist

After deployment:
- [ ] Frontend loads at worker URL
- [ ] Bid/Ask column visible in tables
- [ ] Volume column visible in tables
- [ ] Filters work
- [ ] Data refreshes
- [ ] No console errors

---

**Need Help?** See `DEPLOYMENT_GUIDE.md` for detailed instructions.

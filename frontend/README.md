# OptionsMagic Frontend

Modern web interface for the OptionsMagic options trading screener, built on Cloudflare Workers.

## 🏗️ Architecture

```
frontend/
├── src/
│   └── worker.js          # Cloudflare Worker API backend
├── public/
│   └── index.html         # Static HTML frontend (Alpine.js + Tailwind)
├── wrangler.toml          # Cloudflare Workers configuration
├── package.json           # npm scripts and dependencies
└── .dev.vars.template     # Environment variables template
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ installed
- Cloudflare account (free tier works)
- Supabase project with `options_opportunities` table

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

Create `.dev.vars` for local development:

```bash
cp .dev.vars.template .dev.vars
# Edit .dev.vars and add your Supabase credentials
```

Your `.dev.vars` should contain:

```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_anon_key_here
```

### 3. Run Locally

```bash
npm run dev
```

This starts a local development server at `http://localhost:8787`

## 📦 Deployment

### Manual Deployment

```bash
# Deploy to production
npm run deploy:production

# Deploy to staging
npm run deploy:staging
```

### Automatic Deployment (CI/CD)

The project includes GitHub Actions workflow (`.github/workflows/deploy-frontend.yml`) that:

- ✅ **On PR:** Deploys to staging environment
- ✅ **On merge to main:** Deploys to production environment
- ✅ Automatically sets environment secrets

#### Required GitHub Secrets

Add these in your repo: **Settings → Secrets and variables → Actions**

```
CLOUDFLARE_API_TOKEN       # Get from Cloudflare dashboard
CLOUDFLARE_ACCOUNT_ID      # Your Cloudflare account ID
SUPABASE_URL              # Your Supabase project URL
SUPABASE_KEY              # Your Supabase anon key
```

**How to get Cloudflare API Token:**
1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Create Token → "Edit Cloudflare Workers" template
3. Copy the token and add to GitHub Secrets

## 🔧 Development

### Project Structure

**`src/worker.js`** - API backend
- Handles `/api/options` endpoint
- Handles `/api/expirations` endpoint
- Fetches data from Supabase
- Applies filters and transformations

**`public/index.html`** - Frontend UI
- Alpine.js for reactivity
- Tailwind CSS for styling
- Grouped and flat table views
- Filtering, sorting, pagination
- Bollinger Band indicators
- Technical analysis overlays

### Available Scripts

```bash
npm run dev                  # Start local development server
npm run deploy               # Deploy to default environment
npm run deploy:staging       # Deploy to staging
npm run deploy:production    # Deploy to production
npm run tail                 # Stream logs from deployed worker
npm run tail:production      # Stream production logs
```

## 🌐 API Endpoints

### `GET /api/options`

Fetch filtered options opportunities.

**Query Parameters:**
- `symbol` - Filter by ticker symbol (e.g., `AAPL`)
- `expiration` - Filter by exact expiration date (YYYY-MM-DD)
- `expiration_window` - Filter by days to expiration (`30`, `45`, `60`)
- `long_bias` - Filter for long-bias trades only (`true`/`false`)

**Example:**
```bash
curl "https://your-worker.workers.dev/api/options?expiration_window=45&long_bias=true"
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "opportunity_id": "abc123",
      "symbol": "AAPL",
      "strike": 180.00,
      "expiration": "2026-03-20",
      "annualized_return": 42.5,
      "delta": -0.25,
      "bid": 2.50,
      "ask": 2.55,
      "volume": 1234,
      ...
    }
  ],
  "lastUpdated": "2026-02-10T04:00:00.000Z"
}
```

### `GET /api/expirations`

Get list of available expiration dates.

**Response:**
```json
{
  "success": true,
  "expirations": [
    "2026-02-14",
    "2026-02-21",
    "2026-02-28"
  ]
}
```

## 🎨 Frontend Features

- ✅ **Grouped View** - Group options by ticker with collapsible rows
- ✅ **Flat View** - Traditional table with pagination
- ✅ **Filtering** - Symbol, expiration, return %, delta, long-bias
- ✅ **Sorting** - Click column headers to sort
- ✅ **Technical Indicators** - Bollinger Bands, RSI, SMA200
- ✅ **Real-time Data** - Refresh button to fetch latest opportunities
- ✅ **Responsive Design** - Works on mobile and desktop

## 🔐 Environment Variables

### Production Secrets

Set these via `wrangler secret put`:

```bash
cd frontend
npx wrangler secret put SUPABASE_URL --env production
npx wrangler secret put SUPABASE_KEY --env production
```

### Development Variables

Create `.dev.vars` (gitignored):

```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_anon_key
```

## 📊 Database Requirements

The Worker expects a Supabase table called `options_opportunities` with these columns:

```sql
CREATE TABLE options_opportunities (
  opportunity_id TEXT PRIMARY KEY,
  ticker TEXT,
  strategy_type TEXT,
  expiration_date DATE,
  strike_price NUMERIC,
  width NUMERIC,
  net_credit NUMERIC,
  collateral NUMERIC,
  return_pct NUMERIC,
  annualized_return NUMERIC,
  rsi_14 NUMERIC,
  iv_percentile NUMERIC,
  price_vs_bb_lower NUMERIC,
  above_sma_200 BOOLEAN,
  delta NUMERIC,
  theta NUMERIC,
  bid NUMERIC,
  ask NUMERIC,
  volume INTEGER
);
```

## 🚧 Roadmap

### Phase 1 (Current) ✅
- [x] Extract frontend from inline Worker code
- [x] Add wrangler.toml configuration
- [x] Set up GitHub Actions CI/CD
- [x] Add Bid/Ask and Volume columns

### Phase 2 (Backlog)
- [ ] Connect options-magic.com domain
- [ ] Add Cloudflare Access authentication
- [ ] Set up monitoring (Sentry)

### Phase 3 (Future)
- [ ] Upgrade to Tailwind v3
- [ ] Replace Moment.js with Day.js
- [ ] Add export to CSV
- [ ] Add dark mode
- [ ] Real-time updates (WebSockets)

## 🐛 Troubleshooting

### `Error: Missing SUPABASE_URL or SUPABASE_KEY`

Make sure you've set the environment variables:
- For local dev: Create `.dev.vars`
- For production: Use `wrangler secret put`

### `404 Not Found` on deployed site

Check that:
1. `wrangler.toml` `[site]` configuration is correct
2. `public/index.html` exists
3. You've deployed with `npm run deploy`

### Changes not appearing after deployment

Try:
```bash
# Clear cache and redeploy
npx wrangler deploy --env production --force
```

## 📝 License

ISC

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feature/amazing-feature`
2. Make changes and test locally: `npm run dev`
3. Commit: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request (auto-deploys to staging)

---

**Built with:** Cloudflare Workers, Alpine.js, Tailwind CSS  
**Deployed on:** Cloudflare Edge Network  
**Backend:** Supabase PostgreSQL

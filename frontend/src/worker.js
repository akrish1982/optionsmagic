/**
 * OptionsMagic API Worker
 * Cloudflare Worker for serving options data from Supabase
 * 
 * Endpoints:
 *   - GET / → HTML frontend (from public/index.html)
 *   - GET /api/options → Filtered options data
 *   - GET /api/expirations → Available expiration dates
 */

// CORS headers for API responses
const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Handle OPTIONS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { 
        headers: CORS_HEADERS 
      });
    }

    try {
      // Route: /api/options - Get filtered options opportunities
      if (path === "/api/options" || path === "/api/options/") {
        return handleOptionsRequest(url, env);
      }

      // Route: /api/expirations - Get available expiration dates
      if (path === "/api/expirations" || path === "/api/expirations/") {
        return handleExpirationsRequest(env);
      }

      // Route: / - Serve HTML frontend (handled by Cloudflare Workers static assets)
      // This will be automatically served from public/index.html via wrangler.toml config

      // 404 for unknown routes
      return new Response(
        JSON.stringify({
          success: false,
          error: "Not found",
          path: path,
          availableEndpoints: [
            "GET /",
            "GET /api/options",
            "GET /api/expirations"
          ]
        }),
        {
          status: 404,
          headers: {
            ...CORS_HEADERS,
            "Content-Type": "application/json"
          }
        }
      );

    } catch (error) {
      console.error("Worker error:", error);
      return new Response(
        JSON.stringify({
          success: false,
          error: error.message,
          stack: error.stack
        }),
        {
          status: 500,
          headers: {
            ...CORS_HEADERS,
            "Content-Type": "application/json"
          }
        }
      );
    }
  }
};

/**
 * Handle /api/options endpoint
 * Fetches and filters options opportunities from Supabase
 */
async function handleOptionsRequest(url, env) {
  console.log("Processing /api/options request");

  // Parse query parameters
  const params = url.searchParams;
  const symbol = params.get('symbol') || '';
  const expiration = params.get('expiration') || '';
  const expirationWindow = params.get('expiration_window') || ''; // 30, 45, or 60 days
  const longBiasOnly = params.get('long_bias') === 'true';

  // Build Supabase query
  const supabaseUrl = env.SUPABASE_URL;
  const supabaseKey = env.SUPABASE_KEY;

  console.log("Connecting to Supabase:", supabaseUrl);

  let queryUrl = `${supabaseUrl}/rest/v1/options_opportunities?select=*&limit=500`;

  // Add long-bias filters if requested (above_sma_200=true, rsi_14<45)
  if (longBiasOnly) {
    queryUrl += '&above_sma_200=eq.true&rsi_14=lt.45';
  }

  // Fetch from Supabase
  const response = await fetch(queryUrl, {
    method: 'GET',
    headers: {
      'apikey': supabaseKey,
      'Authorization': `Bearer ${supabaseKey}`,
      'Content-Type': 'application/json',
      'Prefer': 'return=representation'
    }
  });

  console.log("Supabase response status:", response.status);

  if (!response.ok) {
    const errorText = await response.text();
    console.error("Supabase error:", errorText);
    throw new Error(`Supabase error: ${errorText}`);
  }

  const data = await response.json();
  console.log("Got data, count:", data.length);

  // Process and transform data
  const processedData = data.map(item => {
    const today = new Date();
    const expDate = new Date(item.expiration_date);
    const daysToExp = Math.max(1, Math.ceil((expDate - today) / (1000 * 60 * 60 * 24)));

    return {
      opportunity_id: item.opportunity_id,
      symbol: item.ticker,
      strategy_type: item.strategy_type,
      expiration: item.expiration_date,
      strike: item.strike_price,
      width: item.width,
      net_credit: item.net_credit,
      collateral: item.collateral,
      return_pct: item.return_pct,
      annualized_return: item.annualized_return,
      // Technical indicators
      rsi_14: item.rsi_14,
      iv_percentile: item.iv_percentile,
      price_vs_bb_lower: item.price_vs_bb_lower,
      above_sma_200: item.above_sma_200,
      // Greeks
      delta: item.delta,
      theta: item.theta,
      // Calculated fields
      days_to_exp: daysToExp,
      income: item.net_credit,
      at_lower_bb: item.price_vs_bb_lower !== null && item.price_vs_bb_lower <= 2,
      // NEW: Bid/Ask and Volume data
      bid: item.bid,
      ask: item.ask,
      volume: item.volume
    };
  });

  // Apply frontend filters
  let filteredData = processedData.filter(item => {
    if (symbol && item.symbol !== symbol.toUpperCase()) return false;
    if (expiration && item.expiration !== expiration) return false;
    if (expirationWindow) {
      const maxDays = parseInt(expirationWindow, 10);
      if (item.days_to_exp > maxDays) return false;
    }
    // Keep only CSP and VPC strategies
    if (item.strategy_type !== 'CSP' && item.strategy_type !== 'VPC') return false;
    return true;
  });

  console.log("After filtering, count:", filteredData.length);

  // Sort by annualized return (highest first)
  filteredData.sort((a, b) => b.annualized_return - a.annualized_return);

  return new Response(
    JSON.stringify({
      success: true,
      data: filteredData,
      lastUpdated: new Date().toISOString()
    }),
    {
      headers: {
        ...CORS_HEADERS,
        "Content-Type": "application/json"
      }
    }
  );
}

/**
 * Handle /api/expirations endpoint
 * Returns list of available expiration dates
 */
async function handleExpirationsRequest(env) {
  console.log("Processing /api/expirations request");

  const supabaseUrl = env.SUPABASE_URL;
  const supabaseKey = env.SUPABASE_KEY;

  const response = await fetch(`${supabaseUrl}/rest/v1/options_opportunities?select=expiration_date`, {
    headers: {
      'apikey': supabaseKey,
      'Authorization': `Bearer ${supabaseKey}`,
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Supabase error: ${errorText}`);
  }

  const data = await response.json();

  // Extract unique expirations and sort
  const expirations = [...new Set(data.map(item => item.expiration_date))].sort();

  return new Response(
    JSON.stringify({
      success: true,
      expirations
    }),
    {
      headers: {
        ...CORS_HEADERS,
        "Content-Type": "application/json"
      }
    }
  );
}

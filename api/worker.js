// options-api.js - Fixed worker for Supabase
export default {
    async fetch(request, env, ctx) {
      // CORS headers
      const corsHeaders = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Content-Type": "application/json"
      };
  
      // Handle OPTIONS request
      if (request.method === "OPTIONS") {
        return new Response(null, { headers: corsHeaders });
      }
  
      const url = new URL(request.url);
      const path = url.pathname;
  
      try {
        // Log the request for debugging
        console.log("Path requested:", path);
  
        // Handle options endpoint
        if (path === "/api/options" || path === "/api/options/") {
          console.log("Processing options request");
          // Get query parameters
          const params = url.searchParams;
          const symbol = params.get('symbol') || '';
          const expiration = params.get('expiration') || '';
          
          // Instead of using Supabase RPC, use direct SQL query with Supabase REST API
          const supabaseUrl = env.SUPABASE_URL;
          const supabaseKey = env.SUPABASE_KEY;
          
          console.log("Connecting to Supabase:", supabaseUrl);
          
          // For testing, start with a simple query to make sure the connection works
          const response = await fetch(`${supabaseUrl}/rest/v1/tradeable_options?select=*&limit=250`, {
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
          
          // Process the data to match your SQL query requirements
          const processedData = data.map(item => {
            return {
              contractid: item.contractid,
              symbol: item.symbol,
              expiration: item.expiration,
              strike: item.strike,
              type: item.type,
              last: item.last,
              mark: item.mark,
              bid: item.bid,
              bid_size: item.bid_size,
              ask: item.ask,
              ask_size: item.ask_size,
              volume: item.volume,
              open_interest: item.open_interest,
              date: item.date,
              implied_volatility: item.implied_volatility,
              delta: item.delta,
              gamma: item.gamma,
              theta: item.theta,
              vega: item.vega,
              rho: item.rho,
              // Calculate derived fields
              collateral: item.strike * 100,
              income: item.bid * 100,
              return_pct: (item.bid / item.strike) * 100
            };
          });
          
          // Filter the data based on query parameters
          let filteredData = processedData.filter(item => {
            // Filter by symbol if provided
            if (symbol && item.symbol !== symbol) {
              return false;
            }
            
            // Filter by expiration if provided
            if (expiration && item.expiration !== expiration) {
              return false;
            }
            
            // Keep only PUT options
            if (item.type !== 'put') {
              return false;
            }
            
            return true;
          });
          
          // Sort by return percentage
          filteredData.sort((a, b) => b.return_pct - a.return_pct);
          
          return new Response(JSON.stringify({
            success: true,
            data: filteredData,
            lastUpdated: new Date().toISOString()
          }), {
            headers: corsHeaders
          });
        } 
        // Handle expirations endpoint
        else if (path === "/api/expirations") {
          console.log("Processing expirations request");
          
          const supabaseUrl = env.SUPABASE_URL;
          const supabaseKey = env.SUPABASE_KEY;
          
          // Get distinct expirations from the database
          const response = await fetch(`${supabaseUrl}/rest/v1/tradeable_options`, {
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
          
          // Extract unique expirations
          const expirations = [...new Set(data.map(item => item.expiration))].sort();
          
          return new Response(JSON.stringify({
            success: true,
            expirations
          }), {
            headers: corsHeaders
          });
        } 
        else {
          return new Response(JSON.stringify({
            success: false,
            error: "Not found",
            path: path
          }), {
            status: 404,
            headers: corsHeaders
          });
        }
      } catch (error) {
        console.error("Worker error:", error);
        return new Response(JSON.stringify({
          success: false,
          error: error.message
        }), {
          status: 500,
          headers: corsHeaders
        });
      }
    }
  };
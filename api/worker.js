// options-api.js - Fixed worker for Supabase

// HTML page content
const HTML_PAGE = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Options Magic - Options Screener</title>
  <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet" />
  <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.5/dist/cdn.min.js" defer></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.4/moment.min.js"></script>
  <script>
    function optionsApp() {
      return {
        options: [],
        filteredOptions: [],
        displayedOptions: [],
        groupedOptions: {},
        loading: true,
        lastUpdated: '',
        expirationDates: [],
        expandedGroups: {},
        currentPage: 1,
        pageSize: 25,
        sortColumn: 'annualized_return',
        sortDirection: 'desc',
        viewMode: 'grouped',
        filters: {
          symbol: '',
          expiration: '',
          expirationWindow: '',
          minReturn: '',
          maxDelta: '',
          longBiasOnly: false
        },
        init() { this.fetchData(); },
        fetchData() {
          this.loading = true;
          const params = new URLSearchParams();
          if (this.filters.expirationWindow) params.set('expiration_window', this.filters.expirationWindow);
          if (this.filters.longBiasOnly) params.set('long_bias', 'true');
          const queryString = params.toString();
          const url = '/api/options' + (queryString ? '?' + queryString : '');
          fetch(url)
            .then(response => response.json())
            .then(data => {
              this.options = data.data || [];
              this.lastUpdated = data.lastUpdated || new Date().toLocaleString();
              this.expirationDates = [...new Set(this.options.map(opt => opt.expiration))].sort();
              this.applyFilters();
              this.loading = false;
            })
            .catch(error => { console.error('Error:', error); this.loading = false; });
        },
        refreshData() { this.fetchData(); },
        applyFilters() {
          this.filteredOptions = this.options.filter(option => {
            if (this.filters.symbol && !option.symbol.includes(this.filters.symbol.toUpperCase())) return false;
            if (this.filters.expiration && option.expiration !== this.filters.expiration) return false;
            if (this.filters.minReturn && option.annualized_return < parseFloat(this.filters.minReturn)) return false;
            if (this.filters.maxDelta && Math.abs(option.delta) > Math.abs(parseFloat(this.filters.maxDelta))) return false;
            return true;
          });
          this.sortData();
          this.groupBySymbol();
          this.goToPage(1);
        },
        groupBySymbol() {
          this.groupedOptions = {};
          this.filteredOptions.forEach(option => {
            if (!this.groupedOptions[option.symbol]) {
              this.groupedOptions[option.symbol] = {
                symbol: option.symbol,
                at_lower_bb: option.at_lower_bb,
                above_sma_200: option.above_sma_200,
                rsi_14: option.rsi_14,
                current_price: option.current_price,
                options: []
              };
              if (this.expandedGroups[option.symbol] === undefined) this.expandedGroups[option.symbol] = true;
            }
            this.groupedOptions[option.symbol].options.push(option);
          });
        },
        toggleGroup(symbol) { this.expandedGroups[symbol] = !this.expandedGroups[symbol]; },
        get sortedGroups() {
          return Object.values(this.groupedOptions).sort((a, b) => {
            const aMax = Math.max(...a.options.map(o => o.annualized_return || 0));
            const bMax = Math.max(...b.options.map(o => o.annualized_return || 0));
            return bMax - aMax;
          });
        },
        sortBy(column) {
          if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
          } else {
            this.sortColumn = column;
            this.sortDirection = 'desc';
          }
          this.sortData();
        },
        sortData() {
          const direction = this.sortDirection === 'asc' ? 1 : -1;
          this.filteredOptions = [...this.filteredOptions].sort((a, b) => {
            if (a[this.sortColumn] < b[this.sortColumn]) return -1 * direction;
            if (a[this.sortColumn] > b[this.sortColumn]) return 1 * direction;
            return 0;
          });
          this.updateDisplayedOptions();
        },
        updateDisplayedOptions() {
          const start = (this.currentPage - 1) * this.pageSize;
          const end = start + this.pageSize;
          this.displayedOptions = this.filteredOptions.slice(start, end);
        },
        get pageCount() { return Math.max(1, Math.ceil(this.filteredOptions.length / this.pageSize)); },
        nextPage() { if (this.currentPage < this.pageCount) { this.currentPage++; this.updateDisplayedOptions(); } },
        prevPage() { if (this.currentPage > 1) { this.currentPage--; this.updateDisplayedOptions(); } },
        goToPage(page) { this.currentPage = page; this.updateDisplayedOptions(); },
        formatDate(dateStr) { return moment(dateStr).format('MMM D, YYYY'); },
        formatPrice(price) { return price ? price.toFixed(2) : '0.00'; },
        formatCurrency(amount) { return amount ? '$' + amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '$0.00'; },
        formatPercent(value) { return value ? value.toFixed(2) + '%' : '0.00%'; },
        formatDelta(delta) { return delta ? delta.toFixed(3) : '0.000'; },
        formatNumber(num) { return num ? num.toLocaleString() : '0'; },
        formatAnnualizedReturn(value) { return value ? value.toFixed(1) + '%' : '0.0%'; },
        formatDaysToExp(days) { return days ? days + 'd' : '-'; }
      };
    }
  </script>
</head>
<body class="bg-gray-100">
  <div x-data="optionsApp()" x-init="init()" class="min-h-screen">
    <header class="bg-blue-800 text-white shadow-lg">
      <div class="container mx-auto py-4 px-4 md:px-6">
        <div class="flex justify-between items-center">
          <h1 class="text-2xl md:text-3xl font-bold">Options Magic</h1>
          <div class="flex items-center space-x-4">
            <span x-text="lastUpdated" class="text-sm hidden md:block"></span>
            <button @click="refreshData" class="bg-blue-600 hover:bg-blue-700 py-2 px-4 rounded-md text-sm">Refresh</button>
          </div>
        </div>
        <p class="mt-1 text-blue-200 text-sm">Premium Options Screener for Cash-Secured Puts</p>
      </div>
    </header>
    <div class="container mx-auto mt-6 px-4 md:px-6">
      <div class="bg-white rounded-lg shadow-md p-4 md:p-6">
        <div class="flex flex-col space-y-4">
          <div class="flex flex-col md:flex-row md:items-center md:space-x-6 space-y-4 md:space-y-0">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Symbol</label>
              <input x-model="filters.symbol" type="text" class="border border-gray-300 rounded-md px-3 py-2 w-full md:w-32" placeholder="All">
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Expiration Window</label>
              <select x-model="filters.expirationWindow" @change="fetchData()" class="border border-gray-300 rounded-md px-3 py-2 w-full md:w-40">
                <option value="">All Dates</option>
                <option value="30">30 Days</option>
                <option value="45">45 Days</option>
                <option value="60">60 Days</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Min Ann. Return %</label>
              <input x-model="filters.minReturn" type="number" step="1" min="0" class="border border-gray-300 rounded-md px-3 py-2 w-full md:w-32" placeholder="e.g. 20">
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Max Delta</label>
              <input x-model="filters.maxDelta" type="number" step="0.05" min="-1" max="0" class="border border-gray-300 rounded-md px-3 py-2 w-full md:w-32" placeholder="e.g. -0.3">
            </div>
          </div>
          <div class="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
            <div class="flex items-center space-x-6">
              <label class="inline-flex items-center cursor-pointer">
                <input type="checkbox" x-model="filters.longBiasOnly" @change="fetchData()" class="form-checkbox h-5 w-5 text-blue-600 rounded">
                <span class="ml-2 text-sm font-medium text-gray-700">Long Bias Only</span>
              </label>
              <label class="inline-flex items-center cursor-pointer">
                <input type="checkbox" :checked="viewMode === 'grouped'" @change="viewMode = viewMode === 'grouped' ? 'flat' : 'grouped'" class="form-checkbox h-5 w-5 text-blue-600 rounded">
                <span class="ml-2 text-sm font-medium text-gray-700">Group by Ticker</span>
              </label>
            </div>
            <button @click="applyFilters" class="bg-blue-600 hover:bg-blue-700 text-white py-2 px-6 rounded-md">Apply Filters</button>
          </div>
        </div>
      </div>
    </div>
    <main class="container mx-auto mt-6 px-4 md:px-6 pb-12">
      <div x-show="loading" class="flex justify-center items-center py-12">
        <svg class="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span class="ml-3 text-lg text-gray-700">Loading data...</span>
      </div>
      <div x-show="!loading && viewMode === 'grouped'" class="space-y-4">
        <template x-for="group in sortedGroups" :key="group.symbol">
          <div class="bg-white rounded-lg shadow-md overflow-hidden">
            <div @click="toggleGroup(group.symbol)" class="bg-gray-100 px-4 py-3 cursor-pointer hover:bg-gray-200 flex items-center justify-between">
              <div class="flex items-center space-x-3">
                <span x-show="group.at_lower_bb" class="inline-flex items-center justify-center w-3 h-3 bg-green-500 rounded-full" title="At Lower BB"></span>
                <span x-show="!group.at_lower_bb" class="inline-flex items-center justify-center w-3 h-3 bg-gray-300 rounded-full"></span>
                <span class="text-lg font-bold text-blue-600" x-text="group.symbol"></span>
                <span x-show="group.above_sma_200" class="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">Above SMA200</span>
                <span x-show="group.rsi_14" class="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded" x-text="'RSI: ' + (group.rsi_14 ? group.rsi_14.toFixed(1) : '-')"></span>
              </div>
              <div class="flex items-center space-x-3">
                <span class="text-sm text-gray-600" x-text="group.options.length + ' options'"></span>
                <svg :class="{'rotate-180': expandedGroups[group.symbol]}" class="w-5 h-5 text-gray-500 transform transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </div>
            </div>
            <div x-show="expandedGroups[group.symbol]" class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Expiration</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Days</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Strike</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Collateral</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Income</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Return %</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Ann. Return</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Delta</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <template x-for="(option, idx) in group.options" :key="option.opportunity_id">
                    <tr :class="idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'">
                      <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900" x-text="formatDate(option.expiration)"></td>
                      <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-600" x-text="formatDaysToExp(option.days_to_exp)"></td>
                      <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900" x-text="formatPrice(option.strike)"></td>
                      <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900" x-text="formatCurrency(option.collateral)"></td>
                      <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900" x-text="formatCurrency(option.income)"></td>
                      <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900" x-text="formatPercent(option.return_pct)"></td>
                      <td class="px-4 py-2 whitespace-nowrap text-sm font-medium text-green-600" x-text="formatAnnualizedReturn(option.annualized_return)"></td>
                      <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900" x-text="formatDelta(option.delta)"></td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
          </div>
        </template>
        <div x-show="sortedGroups.length === 0" class="bg-white rounded-lg shadow-md p-8 text-center text-gray-500">No options found.</div>
      </div>
      <div x-show="!loading && viewMode === 'flat'" class="bg-white rounded-lg shadow-md overflow-hidden">
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">BB</th>
                <th @click="sortBy('symbol')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer">Symbol</th>
                <th @click="sortBy('expiration')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer">Expiration</th>
                <th @click="sortBy('days_to_exp')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer">Days</th>
                <th @click="sortBy('strike')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer">Strike</th>
                <th @click="sortBy('collateral')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer">Collateral</th>
                <th @click="sortBy('income')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer">Income</th>
                <th @click="sortBy('return_pct')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer">Return %</th>
                <th @click="sortBy('annualized_return')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer">Ann. Return</th>
                <th @click="sortBy('delta')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer">Delta</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <template x-for="(option, index) in displayedOptions" :key="option.opportunity_id">
                <tr :class="index % 2 === 0 ? 'bg-white' : 'bg-gray-50'">
                  <td class="px-4 py-3 whitespace-nowrap">
                    <span x-show="option.at_lower_bb" class="inline-flex items-center justify-center w-3 h-3 bg-green-500 rounded-full"></span>
                    <span x-show="!option.at_lower_bb" class="inline-flex items-center justify-center w-3 h-3 bg-gray-300 rounded-full"></span>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-blue-600" x-text="option.symbol"></td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900" x-text="formatDate(option.expiration)"></td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600" x-text="formatDaysToExp(option.days_to_exp)"></td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900" x-text="formatPrice(option.strike)"></td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900" x-text="formatCurrency(option.collateral)"></td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900" x-text="formatCurrency(option.income)"></td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900" x-text="formatPercent(option.return_pct)"></td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-green-600" x-text="formatAnnualizedReturn(option.annualized_return)"></td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900" x-text="formatDelta(option.delta)"></td>
                </tr>
              </template>
              <tr x-show="displayedOptions.length === 0">
                <td colspan="10" class="px-4 py-8 text-center text-gray-500">No options found.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200">
          <p class="text-sm text-gray-700">
            Showing <span class="font-medium" x-text="(currentPage - 1) * pageSize + 1"></span> to
            <span class="font-medium" x-text="Math.min(currentPage * pageSize, filteredOptions.length)"></span> of
            <span class="font-medium" x-text="filteredOptions.length"></span>
          </p>
          <nav class="inline-flex rounded-md shadow-sm -space-x-px">
            <button @click="prevPage" :disabled="currentPage === 1" class="px-3 py-2 border border-gray-300 bg-white text-sm text-gray-500 hover:bg-gray-50" :class="{'opacity-50': currentPage === 1}">Prev</button>
            <button @click="nextPage" :disabled="currentPage === pageCount" class="px-3 py-2 border border-gray-300 bg-white text-sm text-gray-500 hover:bg-gray-50" :class="{'opacity-50': currentPage === pageCount}">Next</button>
          </nav>
        </div>
      </div>
      <div x-show="!loading" class="mt-4 bg-white rounded-lg shadow-md p-4">
        <div class="flex flex-wrap gap-6 text-sm text-gray-600">
          <div>Total Options: <span class="font-semibold text-gray-900" x-text="filteredOptions.length"></span></div>
          <div>Unique Tickers: <span class="font-semibold text-gray-900" x-text="Object.keys(groupedOptions).length"></span></div>
          <div>At Lower BB: <span class="font-semibold text-green-600" x-text="filteredOptions.filter(o => o.at_lower_bb).length"></span></div>
        </div>
      </div>
    </main>
    <footer class="bg-gray-800 text-white py-6">
      <div class="container mx-auto px-4 md:px-6">
        <div class="flex flex-col md:flex-row justify-between items-center">
          <p class="text-sm">Options Magic</p>
          <p class="text-sm text-gray-400 mt-2 md:mt-0">Data refreshed: <span x-text="lastUpdated"></span></p>
        </div>
      </div>
    </footer>
  </div>
</body>
</html>`;

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

        // Serve HTML page at root
        if (path === "/" || path === "") {
          return new Response(HTML_PAGE, {
            headers: {
              "Content-Type": "text/html;charset=UTF-8",
              "Cache-Control": "no-cache"
            }
          });
        }

        // Handle options endpoint
        if (path === "/api/options" || path === "/api/options/") {
          console.log("Processing options request");
          // Get query parameters
          const params = url.searchParams;
          const symbol = params.get('symbol') || '';
          const expiration = params.get('expiration') || '';
          const expirationWindow = params.get('expiration_window') || ''; // 30, 45, or 60 days
          const longBiasOnly = params.get('long_bias') === 'true'; // Filter for above_sma_200 and low RSI

          // Instead of using Supabase RPC, use direct SQL query with Supabase REST API
          const supabaseUrl = env.SUPABASE_URL;
          const supabaseKey = env.SUPABASE_KEY;

          console.log("Connecting to Supabase:", supabaseUrl);

          // Build query with filters
          let queryUrl = `${supabaseUrl}/rest/v1/options_opportunities?select=*&limit=500`;

          // Add long-bias filters if requested (above_sma_200=true, rsi_14<45)
          if (longBiasOnly) {
            queryUrl += '&above_sma_200=eq.true&rsi_14=lt.45';
          }

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

          // Debug: log first record to see field values
          if (data.length > 0) {
            console.log("Sample record type field:", data[0].type);
            console.log("Sample record keys:", Object.keys(data[0]).join(', '));
          }
          
          // Process the data - map to match actual options_opportunities table schema
          const processedData = data.map(item => {
            // Calculate days to expiration
            const today = new Date();
            const expDate = new Date(item.expiration_date);
            const daysToExp = Math.max(1, Math.ceil((expDate - today) / (1000 * 60 * 60 * 24)));

            return {
              // Map from actual table columns
              opportunity_id: item.opportunity_id,
              symbol: item.ticker,
              strategy_type: item.strategy_type,  // 'CSP' or 'VPC'
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
              income: item.net_credit,  // net_credit is the income
              // Bollinger Band indicator: true if price is near/at lower BB (within 2%)
              at_lower_bb: item.price_vs_bb_lower !== null && item.price_vs_bb_lower <= 2
            };
          });
          
          // Filter the data based on query parameters
          let filteredData = processedData.filter(item => {
            // Filter by symbol if provided
            if (symbol && item.symbol !== symbol.toUpperCase()) {
              return false;
            }

            // Filter by exact expiration if provided
            if (expiration && item.expiration !== expiration) {
              return false;
            }

            // Filter by expiration window (30, 45, or 60 days)
            if (expirationWindow) {
              const maxDays = parseInt(expirationWindow, 10);
              if (item.days_to_exp > maxDays) {
                return false;
              }
            }

            // Keep only CSP (Cash Secured Put) strategies by default
            // VPC (Vertical Put Credit) spreads are also valid put strategies
            if (item.strategy_type !== 'CSP' && item.strategy_type !== 'VPC') {
              return false;
            }

            return true;
          });

          console.log("After filtering, count:", filteredData.length);

          // Sort by annualized return (highest first)
          filteredData.sort((a, b) => b.annualized_return - a.annualized_return);
          
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
          const response = await fetch(`${supabaseUrl}/rest/v1/options_opportunities`, {
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
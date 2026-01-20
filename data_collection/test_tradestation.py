from data_collection.tradestation_options import *                                                                                  
                                                                                                                                
api = TradeStationAPI()                                                                                                             
api.refresh_access_token()                                                                                                          
supabase = get_supabase_client()                                                                                                    
                                                                                                                                
# Test with AAPL (90 day expirations)                                                                                               
count = fetch_options_for_ticker(api, supabase, 'AAPL', max_days=90)                                                                
print(f'Stored {count} AAPL options')                                                                                               
                                                                                                                                
# Check one record to verify data                                                                                                   
result = supabase.table('options_quotes').select('*').eq('symbol', 'AAPL').limit(3).execute()                                       
for row in result.data:                                                                                                             
    print(f"{row['contractid']}: bid={row['bid']}, ask={row['ask']}, delta={row['delta']}, iv={row['implied_volatility']}") 
# import requests                                                                                                                     
# import json                                                                                                                         
# from data_collection.tradestation_options import *                                                                                  
                                                                                                                                      
# api = TradeStationAPI()                                                                                                             
# api.refresh_access_token()                                                                                                          
# supabase = get_supabase_client()                                                                                                    
                                                                                                                                    
# # Test with AAPL (2 expirations only)                                                                                               
# count = fetch_options_for_ticker(api, supabase, 'AAPL', num_expirations=2)                                                          
# print(f'Stored {count} AAPL options')                                                                                                                                  
# # Load tokens and check scopes                                                                                                      
# with open('tokens.json') as f:                                                                                                      
#     tokens = json.load(f)                                                                                                           
                                                                                                                                    
# r = requests.post('https://signin.tradestation.com/oauth/token',                                                                    
#     data={                                                                                                                          
#         'grant_type': 'refresh_token',                                                                                              
#         'client_id': tokens['client_id'],                                                                                           
#         'client_secret': tokens['client_secret'],                                                                                   
#         'refresh_token': tokens['refresh_token']                                                                                    
#     })                                                                                                                              
                                                                                                                                    
# if r.ok:                                                                                                                            
#     data = r.json()                                                                                                                 
#     print('Current scopes:', data.get('scope'))                                                                                     
#     print()                                                                                                                         
                                                                                                                                    
#     # Check if OptionSpreads is present                                                                                             
#     scopes = data.get('scope', '')                                                                                                  
#     if 'OptionSpreads' not in scopes:                                                                                               
#         print('❌ Missing OptionSpreads scope! You need to re-authorize.')                                                          
#         print('   Run: poetry run python data_collection/tradestation_oauth_setup.py')                                              
#     else:                                                                                                                           
#         print('✓ OptionSpreads scope present')                                                                                      
                                                                                                                                    
#         # Test options endpoint                                                                                                     
#         headers = {'Authorization': f'Bearer {data["access_token"]}'}                                                             
#         r2 = requests.get('https://api.tradestation.com/v3/marketdata/options/expirations/AAPL', headers=headers)                   
#         print(f'Options expirations test: {r2.status_code}')                                                                        
#         if r2.ok:                                                                                                                   
#             exps = r2.json().get('Expirations', [])                                                                                 
#             print(f'  Found {len(exps)} expirations')                                                                               
#         else:                                                                                                                       
#             print(f'  Error: {r2.text[:200]}')                                                                                      
# else:                                                                                                                               
#     print('Token refresh failed:', r.text)   

# import requests                                                                                                                     
# import json                        
# from data_collection.tradestation_options import *                                                                                  
                                                                                                                                    
# api = TradeStationAPI()                                                                                                             
# api.refresh_access_token()                                                                                                          
# supabase = get_supabase_client()                                                                                                    
                                                                                                                                    
# # Test with one ticker                                                                                                              
# count = fetch_options_for_ticker(api, supabase, 'AAPL', num_expirations=2)                                                          
# print(f'Stored {count} AAPL options')                                                                                                      
                                                                                                                                    
# # Load your tokens                                                                                                                  
# with open('tokens.json') as f:                                                                                      
#     tokens = json.load(f)                                                                                                           
                                                                                                                                    
# # Get a fresh access token                                                                                                          
# response = requests.post(                                                                                                           
#     'https://signin.tradestation.com/oauth/token',                                                                                  
#     headers={'Content-Type': 'application/x-www-form-urlencoded'},                                                                  
#     data={                                                                                                                          
#         'grant_type': 'refresh_token',                                                                                              
#         'client_id': tokens['client_id'],                                                                                           
#         'client_secret': tokens['client_secret'],                                                                                   
#         'refresh_token': tokens['refresh_token']                                                                                    
#     }                                                                                                                               
# )                                                                                                                                   
                                                                                                                                    
# if response.ok:                                                                                                                     
#     data = response.json()                                                                                                          
#     print('Scopes granted:', data.get('scope', 'none'))                                                                             
#     print()                                                                                                                         
                                                                                                                                    
#     access_token = data['access_token']                                                                                             
#     headers = {'Authorization': f'Bearer {access_token}'}                                                                           
                                                                                                                                    
#     # Test accounts endpoint                                                                                                        
#     print('Testing /brokerage/accounts...')                                                                                         
#     r = requests.get('https://api.tradestation.com/v3/brokerage/accounts', headers=headers)                                         
#     print(f'  Status: {r.status_code}')                                                                                             
#     if r.ok:                                                                                                                        
#         accounts = r.json().get('Accounts', [])                                                                                     
#         print(f'  Found {len(accounts)} account(s)')                                                                                
#         for acc in accounts:                                                                                                        
#             acc_id = acc.get('AccountID', 'unknown')                                                                                
#             acc_type = acc.get('AccountType', 'unknown')                                                                            
#             print(f'    - {acc_id} ({acc_type})')                                                                                   
                                                                                                                                    
#             # Test positions for this account                                                                                       
#             print(f'  Testing positions for {acc_id}...')                                                                           
#             r2 = requests.get(f'https://api.tradestation.com/v3/brokerage/accounts/{acc_id}/positions', headers=headers)            
#             print(f'    Status: {r2.status_code}')                                                                                  
#             if r2.ok:                                                                                                               
#                 positions = r2.json().get('Positions', [])                                                                          
#                 print(f'    Found {len(positions)} position(s)')                                                                    
#                 for pos in positions[:5]:  # Show first 5                                                                           
#                     symbol = pos.get('Symbol', '?')                                                                                 
#                     qty = pos.get('Quantity', 0)                                                                                    
#                     print(f'      - {symbol}: {qty}')                                                                               
#     else:                                                                                                                           
#         print(f'  Error: {r.text[:200]}')                                                                                           
# else:                                                                                                                               
#     print('Token refresh failed:', response.text)                                                                                   

import json
import requests

with open('tokens.json') as f:                                                                                      
    tokens = json.load(f)                                                                                                           
r = requests.post('https://signin.tradestation.com/oauth/token',                                                                    
    data={'grant_type': 'refresh_token', 'client_id': tokens['client_id'],                                                          
        'client_secret': tokens['client_secret'], 'refresh_token': tokens['refresh_token']})                                      
print('Scopes:', r.json().get('scope', 'error'))
# Load your tokens                                                                                                                  
with open('tokens.json') as f:                                                                                      
    tokens = json.load(f)                                                                                                           
                                                                                                                                    
# Get a fresh access token                                                                                                          
response = requests.post(                                                                                                           
    'https://signin.tradestation.com/oauth/token',                                                                                  
    headers={'Content-Type': 'application/x-www-form-urlencoded'},                                                                  
    data={                                                                                                                          
        'grant_type': 'refresh_token',                                                                                              
        'client_id': tokens['client_id'],                                                                                           
        'client_secret': tokens['client_secret'],                                                                                   
        'refresh_token': tokens['refresh_token']                                                                                    
    }                                                                                                                               
)                                                                                                                                   
                                                                                                                                    
data = response.json()                                                                                                              
access_token = data['access_token']                                                                                                 
headers = {'Authorization': f'Bearer {access_token}'}                                                                               
                                                                                                                                    
print('Testing market data endpoints...')                                                                                           
print()                                                                                                                             
                                                                                                                                    
# Test basic quote first                                                                                                            
print('1. Basic stock quote (AAPL):')                                                                                               
r = requests.get('https://api.tradestation.com/v3/marketdata/quotes/AAPL', headers=headers)                                         
print(f'   Status: {r.status_code}')                                                                                                
print(f'   Response: {r.text[:300]}')                                                                                               
print()                                                                                                                             
                                                                                                                                    
# Test option expirations                                                                                                           
print('2. Option expirations (AAPL):')                                                                                              
r = requests.get('https://api.tradestation.com/v3/marketdata/options/expirations/AAPL', headers=headers)                            
print(f'   Status: {r.status_code}')                                                                                                
print(f'   Response: {r.text[:300]}')                                                                                               
print()                                                                                                                             
                                                                                                                                    
# Test option strikes                                                                                                               
print('3. Option strikes (AAPL):')                                                                                                  
r = requests.get('https://api.tradestation.com/v3/marketdata/options/strikes/AAPL', headers=headers)                                
print(f'   Status: {r.status_code}')                                                                                                
print(f'   Response: {r.text[:300]}')                                                                                               
print()                                                                                                                             
                                                                                                                                    
# Test with a symbol you own (QQQ)                                                                                                  
print('4. Option expirations (QQQ - you have positions):')                                                                          
r = requests.get('https://api.tradestation.com/v3/marketdata/options/expirations/QQQ', headers=headers)                             
print(f'   Status: {r.status_code}')                                                                                                
print(f'   Response: {r.text[:300]}') 
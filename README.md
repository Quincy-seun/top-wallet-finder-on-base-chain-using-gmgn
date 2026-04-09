Finding the most profitable traders on base chain for monitoring, copy-trading etc.
Install python and pip before use.

# ⚡How to use
1. Clone or download the repository
```
git clone https://github.com/Quincy-seun/top-wallet-finder-on-base-chain-using-gmgn.git 
cd top-wallet-finder-on-base-chain-using-gmgn
```
2. Install dependencies
```
pip install -r requirements.txt
```

3. Run the script in this order:
- To fetch memecoins on base chain within X timeframe (1m, 5m, 1h, 6h, 24h) - You can adjust this in line 19 of basecoins.py
```
python basecoins.py
```
- To fetch top traders from memecoins that were found in the previous step - You can change config from line 18-35 in base.py
```
python base.py
```
- Adding strict filters that weed out bots/unprofitable wallets to save time - Adjust in the link on line 43 [1d, 7d, 30d]
```
python refined.py
```
4. Wallets saved to baserefined.csv
5. Check wallet pnl calendar on gmgn.ai to confirm whether it is suitable for copytrading or not (avg holding duration, avg number of buys vs sells etc)
_________________
# 🧪 How It Works
1. Scans gmgn website for memecoins that were created within specified timeframe
2. Fetches the top traders for each coin that was scanned
3. Selects wallets that appear multiple times across scanned coins (usually an indicator of a good trader)
4. Applies stricter profit filters to further narrow down the fetched wallets
_______________
# Need Help?
Send a message on [Telegram](https://t.me/ruby_lanshi)
_______________
# Support me if you find this useful

EVM:
```
0x5534B7a62A7313f78a2B526300b29342BdeE2580
```
Solana: 
```
AbifdZMtuUWcYBnu1tJrRgDecrp9yT8bahFenP8NgADU
```

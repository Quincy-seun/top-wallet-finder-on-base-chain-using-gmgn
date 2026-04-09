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
- To fetch top traders from memecoins that were found in the previous step - You can change config from line 18-35
```
python base.py
```
- Adding strict filters that weeds out bots/unprofitable wallets to save time
```
python refined.py
```
4. Wallets saved to baserefined.csv

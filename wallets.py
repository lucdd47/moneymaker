import os
import json
import base64
import requests
import httpx
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

def load_wallets():
    wallets = []
    for i in range(1, 11):
        seed = os.getenv(f"WALLET_{i}")
        if not seed:
            print(f"⚠️ WALLET_{i} missing")
            continue
        try:
            wallets.append(keypair_from_seed(seed))
        except Exception as e:
            print(f"❌ WALLET_{i} load error: {e}")
    return wallets

def keypair_from_seed(seed_phrase):
    seed_bytes = Bip39SeedGenerator(seed_phrase).Generate()
    bip44 = Bip44.FromSeed(seed_bytes, Bip44Coins.SOLANA)
    private_key = bip44.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0).PrivateKey().Raw().ToBytes()
    return Keypair.from_seed(private_key)

def send_signed_tx(wallet: Keypair, tx_base64: str):
    try:
        tx_bytes = base64.b64decode(tx_base64)
        txn = VersionedTransaction.from_bytes(tx_bytes)
        txn.sign([wallet])
        raw_tx = base64.b64encode(txn.serialize()).decode()
        res = httpx.post(
            "https://api.mainnet-beta.solana.com",
            json={"jsonrpc": "2.0", "id": 1, "method": "sendTransaction", "params": [raw_tx, {"skipPreflight": True}]}
        )
        txid = res.json().get("result")
        if txid:
            print(f"✅ TX sent: https://solscan.io/tx/{txid}")
        else:
            print(f"❌ TX failed: {res.text}")
    except Exception as e:
        print(f"❌ TX error: {e}")

def buy_token_jupiter(wallet: Keypair, mint_address: str):
    try:
        q = requests.get("https://quote-api.jup.ag/v6/quote", params={
            "inputMint": "So11111111111111111111111111111111111111112",
            "outputMint": mint_address,
            "amount": 1_000_000,
            "slippage": 1
        })
        routes = q.json().get("routes", [])
        if not routes:
            print("❌ Buy quote failed")
            return
        sr = requests.post("https://quote-api.jup.ag/v6/swap", headers={"Content-Type": "application/json"}, data=json.dumps({
            "route": routes[0],
            "userPublicKey": str(wallet.pubkey()),
            "wrapUnwrapSOL": True,
            "computeUnitPriceMicroLamports": 1
        }))
        swap_tx = sr.json().get("swapTransaction")
        if not swap_tx:
            print("❌ Buy swap failed")
            return
        send_signed_tx(wallet, swap_tx)
    except Exception as e:
        print(f"❌ Buy error: {e}")

def sell_token_jupiter(wallet: Keypair, mint_address: str):
    try:
        q = requests.get("https://quote-api.jup.ag/v6/quote", params={
            "inputMint": mint_address,
            "outputMint": "So11111111111111111111111111111111111111112",
            "amount": 1_000_000,
            "slippage": 1
        })
        routes = q.json().get("routes", [])
        if not routes:
            print("❌ Sell quote failed")
            return
        sr = requests.post("https://quote-api.jup.ag/v6/swap", headers={"Content-Type": "application/json"}, data=json.dumps({
            "route": routes[0],
            "userPublicKey": str(wallet.pubkey()),
            "wrapUnwrapSOL": True,
            "computeUnitPriceMicroLamports": 1
        }))
        swap_tx = sr.json().get("swapTransaction")
        if not swap_tx:
            print("❌ Sell swap failed")
            return
        send_signed_tx(wallet, swap_tx)
    except Exception as e:
        print(f"❌ Sell error: {e}")

def buy_token_with_all_wallets(mint_address: str):
    for i, wallet in enumerate(load_wallets(), 1):
        print(f"🟢 Wallet {i} buying {mint_address}")
        buy_token_jupiter(wallet, mint_address)

def sell_token_with_all_wallets(mint_address: str):
    for i, wallet in enumerate(load_wallets(), 1):
        print(f"🔴 Wallet {i} selling {mint_address}")
        sell_token_jupiter(wallet, mint_address)

def fetch_market_data(mint_address: str):
    try:
        r = requests.get(f"https://api.dexscreener.com/latest/dex/pairs/solana/{mint_address}")
        if r.ok:
            pair = r.json().get("pair", {})
            return {"priceUsd": pair.get("priceUsd", "N/A"), "marketCap": pair.get("marketCap", "N/A")}
    except Exception as e:
        print(f"❌ DexScreener error: {e}")
    return None

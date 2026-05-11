import os
import time
import requests
from twilio.rest import Client
from datetime import datetime, timedelta

# ─── TWILIO CONFIG ──────────────────────────────────────────────────────────────────────────────
ACCOUNT_SID  = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN   = os.environ.get("TWILIO_AUTH_TOKEN")
SANDBOX_FROM = "whatsapp:+14155238886"
MY_WHATSAPP  = "whatsapp:+15148339119"

# ─── TCG API CONFIG ─────────────────────────────────────────────────────────────────────────────
TCG_API_KEY  = os.environ.get("TCG_API_KEY")
TCG_BASE_URL = "https://api.tcgapi.dev/v1"

# ─── MY CARDS ─────────────────────────────────────────────────────────────────────────────────────
MY_CARDS = {
    "Luffy OP13-118 CGC Pristine 10": {"name": "Luffy", "set": "OP13", "number": "118", "game": "one-piece"},
    "Deoxys VSTAR GG46 CGC Pristine 10": {"name": "Deoxys VSTAR", "set": "GG46", "number": "GG46", "game": "pokemon"},
}

# ─── ONE PIECE WATCHLIST ────────────────────────────────────────────────────────────
ONE_PIECE_WATCHLIST = {
    "Zoro OP13-119 CGC 10": {"name": "Zoro", "set": "OP13", "number": "119", "game": "one-piece"},
    "Sanji OP13-117 CGC 10": {"name": "Sanji", "set": "OP13", "number": "117", "game": "one-piece"},
    "Nami OP13-116 CGC 10": {"name": "Nami", "set": "OP13", "number": "116", "game": "one-piece"},
    "Gol D Roger OP13-118 CGC 10": {"name": "Gol D Roger", "set": "OP13", "number": "118", "game": "one-piece"},
}

# ─── POKEMON WATCHLIST ──────────────────────────────────────────────────────────────────
POKEMON_WATCHLIST = {
    "Charizard ex 199 PSA 10": {"name": "Charizard ex", "number": "199", "game": "pokemon"},
    "Umbreon VMAX Alt Art PSA 10": {"name": "Umbreon VMAX", "number": "215", "game": "pokemon"},
    "Pikachu VMAX Rainbow PSA 10": {"name": "Pikachu VMAX", "number": "188", "game": "pokemon"},
    "Rayquaza VMAX Alt Art PSA 10": {"name": "Rayquaza VMAX", "number": "218", "game": "pokemon"},
    "API TEST": {"name": "Pikachu", "number": "1", "game": "pokemon"},
}

# ─── TCG API FUNCTIONS ─────────────────────────────────────────────────────────────────────────

def get_card_price(card_info):
    try:
        headers = {"x-api-key": TCG_API_KEY}
        params = {
            "q": card_info["name"],
            "game": card_info["game"],
            "number": card_info.get("number", ""),
        }
        resp = requests.get(f"{TCG_BASE_URL}/cards", headers=headers, params=params, timeout=10)
        print(f"TCG API [{card_info['name']}]: {resp.status_code} {resp.text[:300]}")
        data = resp.json()
        cards = data.get("data", [])
        if not cards:
            return None, None
        card = cards[0]
        prices = card.get("prices", {})
        market = prices.get("market") or prices.get("mid") or prices.get("low")
        change_7d = card.get("price_change_7d") or card.get("priceChange7d")
        return market, change_7d
    except Exception as e:
        print(f"TCG API error [{card_info['name']}]: {e}")
        return None, None


def calc_pct(change_7d):
    return change_7d if change_7d is not None else None


# ─── SECTION BUILDERS ─────────────────────────────────────────────────────────────────────────────

def build_my_cards_section():
    lines = ["━━━━━━━━━━━━━━━", "💎 MY CARDS", "━━━━━━━━━━━━━━━"]
    for name, info in MY_CARDS.items():
        price, change = get_card_price(info)
        lines.append(f"\n{name}")
        if not price:
            lines.append("  No price data found")
            continue
        lines.append(f"Market: ${price:.0f}")
        if change is not None:
            arrow = "▲" if change >= 0 else "▼"
            lines.append(f"7d change: {arrow} {abs(change):.1f}%")
        time.sleep(0.5)
    return "\n".join(lines)


def build_watchlist_section(title, emoji, watchlist):
    lines = [f"\n━━━━━━━━━━━━━━━", f"{emoji} {title}", "━━━━━━━━━━━━━━━"]
    for name, info in watchlist.items():
        price, change = get_card_price(info)
        flag = ""
        if change is not None:
            if change >= 15:
                flag = " 🚀"
            elif change <= -15:
                flag = " ⚠️"
        lines.append(f"\n{name}{flag}")
        if not price:
            lines.append("  No price data found")
            continue
        lines.append(f"Market: ${price:.0f}")
        if change is not None:
            arrow = "▲" if change >= 0 else "▼"
            lines.append(f"7d change: {arrow} {abs(change):.1f}%")
        time.sleep(0.5)
    return "\n".join(lines)


def build_hype_radar_section(title, emoji, subreddit, watchlist):
    lines = [f"\n━━━━━━━━━━━━━━━", f"{emoji} HYPE RADAR — {title}", "━━━━━━━━━━━━━━━"]
    reddit_mentions = {}
    try:
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=50"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        posts = r.json().get("data", {}).get("children", [])
        cutoff = datetime.utcnow() - timedelta(hours=24)
        for post in posts:
            data = post.get("data", {})
            created = datetime.utcfromtimestamp(data.get("created_utc", 0))
            if created < cutoff:
                continue
            text = (data.get("title", "") + " " + data.get("selftext", "")).lower()
            for card_name, info in watchlist.items():
                if info["name"].lower() in text:
                    reddit_mentions[card_name] = reddit_mentions.get(card_name, 0) + 1
        time.sleep(1)
    except Exception as e:
        lines.append(f"Reddit fetch error: {e}")
    hype_cards = []
    for name, info in watchlist.items():
        mentions = reddit_mentions.get(name, 0)
        if mentions >= 3:
            price, change = get_card_price(info)
            if change and change >= 15:
                hype_cards.append((name, mentions, change, price))
    if not hype_cards:
        lines.append("No hype signals today.")
    else:
        for name, mentions, change, price in hype_cards:
            lines.append(f"\n{name}")
            lines.append(f"Reddit mentions (24hr): {mentions}")
            lines.append(f"7d price change: +{change:.1f}%")
            if price:
                lines.append(f"Market: ${price:.0f}")
    return "\n".join(lines)


# ─── MAIN ─────────────────────────────────────────────────────────────────────────────────────

def build_message():
    now_est = datetime.utcnow() - timedelta(hours=5)
    today = now_est.strftime("%a %b %-d")
    lines = [f"📈 CARD BRIEFING — {today}"]
    lines.append(build_my_cards_section())
    lines.append(build_watchlist_section("ONE PIECE WATCHLIST", "🏴‍☠️", ONE_PIECE_WATCHLIST))
    lines.append(build_watchlist_section("POKEMON WATCHLIST", "⚡", POKEMON_WATCHLIST))
    lines.append(build_hype_radar_section("ONE PIECE", "🔥", "OnePieceTCG", ONE_PIECE_WATCHLIST))
    lines.append(build_hype_radar_section("POKEMON", "🔥", "PokemonTCG", POKEMON_WATCHLIST))
    return "\n".join(lines)


def send_whatsapp(body):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    message = client.messages.create(
        body=body,
        from_=SANDBOX_FROM,
        to=MY_WHATSAPP,
    )
    print(f"Sent! SID: {message.sid}")


if __name__ == "__main__":
    print("Building message...")
    msg = build_message()
    print(msg)
    print("Sending WhatsApp message...")
    send_whatsapp(msg)

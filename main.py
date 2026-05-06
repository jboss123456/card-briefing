import os
import requests
from bs4 import BeautifulSoup
from twilio.rest import Client
from datetime import datetime, timedelta
import time
import re

# ─── TWILIO CONFIG ────────────────────────────────────────────────────────────
ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
AUTH_TOKEN  = os.environ.get('TWILIO_AUTH_TOKEN')
SANDBOX_FROM = "whatsapp:+14155238886"        # Twilio sandbox number (don't change)
MY_WHATSAPP  = "whatsapp:+15148339119"        # Your WhatsApp number
# ─────────────────────────────────────────────────────────────────────────────

# ─── MY CARDS ─────────────────────────────────────────────────────────────────
MY_CARDS = {
    "Luffy OP13-118 CGC Pristine 10":    "luffy+op13-118+CGC+pristine+10",
    "Deoxys VSTAR GG46 CGC Pristine 10": "deoxys+vstar+GG46+CGC+pristine+10",
}

# ─── ONE PIECE WATCHLIST ──────────────────────────────────────────────────────
ONE_PIECE_WATCHLIST = {
    "Zoro OP13-119 CGC 10":        "zoro+op13-119+CGC+10",
    "Sanji OP13-117 CGC 10":       "sanji+op13-117+CGC+10",
    "Nami OP13-116 CGC 10":        "nami+op13-116+CGC+10",
    "Gol D Roger OP13-118 CGC 10": "gol+d+roger+op13-118+CGC+10",
}

# ─── POKEMON WATCHLIST ────────────────────────────────────────────────────────
POKEMON_WATCHLIST = {
    "Charizard ex 199 PSA 10":      "charizard+ex+199+PSA+10",
    "Umbreon VMAX Alt Art PSA 10":  "umbreon+vmax+alt+art+PSA+10",
    "Pikachu VMAX Rainbow PSA 10":  "pikachu+vmax+rainbow+PSA+10",
    "Rayquaza VMAX Alt Art PSA 10": "rayquaza+vmax+alt+art+PSA+10",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def scrape_ebay_sold(search_query):
    url = (
        f"https://www.ebay.com/sch/i.html?_nkw={search_query}"
        f"&LH_Sold=1&LH_Complete=1&_sop=13"
    )
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".s-item__info")
        for item in items:
            price_tag = item.select_one(".s-item__price")
            date_tag  = item.select_one(".s-item__ended-date, .s-item__listingDate")
            if price_tag:
                raw = price_tag.get_text(strip=True)
                match = re.search(r"\$[\d,]+\.?\d*", raw)
                if match:
                    price_str = match.group(0)
                    price_val = float(price_str.replace("$", "").replace(",", ""))
                    date_str  = date_tag.get_text(strip=True) if date_tag else "N/A"
                    results.append((price_val, date_str, price_str))
        time.sleep(1.5)
    except Exception as e:
        print(f"Scrape error: {e}")
    return results

def calc_avg(sales):
    if not sales:
        return None
    return sum(p for p, d, ps in sales) / len(sales)

def build_my_cards_section():
    lines = ["━━━━━━━━━━━━━━━", "💎 MY CARDS", "━━━━━━━━━━━━━━━"]
    for name, query in MY_CARDS.items():
        recent = scrape_ebay_sold(query)[:10]
        lines.append(f"\n{name}")
        if not recent:
            lines.append("  No recent sales found")
            continue
        avg = calc_avg(recent)
        if avg:
            lines.append(f"30-day avg: ${avg:.0f}")
        for price_val, date_str, price_str in recent[:5]:
            lines.append(f"  • {price_str} — {date_str}")
        if len(recent) < 3:
            lines.append(f"  ⚠ Low volume — {len(recent)} sale(s) found")
    return "\n".join(lines)

def build_watchlist_section(title, emoji, watchlist):
    lines = [f"\n━━━━━━━━━━━━━━━", f"{emoji} {title}", "━━━━━━━━━━━━━━━"]
    for name, query in watchlist.items():
        recent = scrape_ebay_sold(query)[:10]
        prior  = scrape_ebay_sold(query + "+2024")[:10]
        avg_recent = calc_avg(recent)
        avg_prior  = calc_avg(prior)
        pct = None
        if avg_recent and avg_prior and avg_prior > 0:
            pct = ((avg_recent - avg_prior) / avg_prior) * 100
        flag = ""
        if pct is not None:
            if pct >= 15:
                flag = " 🚀"
            elif pct <= -15:
                flag = " ⚠️"
        lines.append(f"\n{name}{flag}")
        if not recent:
            lines.append("  No recent sales found")
            continue
        latest_price, latest_date, latest_str = recent[0]
        lines.append(f"Latest: {latest_str} — {latest_date}")
        if avg_recent:
            if pct is not None:
                arrow = "▲" if pct >= 0 else "▼"
                lines.append(f"30-day avg: ${avg_recent:.0f} | {arrow} {abs(pct):.1f}%")
            else:
                lines.append(f"30-day avg: ${avg_recent:.0f}")
        for price_val, date_str, price_str in recent[1:4]:
            lines.append(f"  • {price_str} — {date_str}")
        if len(recent) < 3:
            lines.append(f"  Low volume — {len(recent)} sale(s) found")
    return "\n".join(lines)

def build_hype_radar_section(title, emoji, subreddit, watchlist):
    lines = [f"\n━━━━━━━━━━━━━━━", f"{emoji} HYPE RADAR — {title}", "━━━━━━━━━━━━━━━"]
    reddit_mentions = {}
    try:
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=50"
        r = requests.get(url, headers={"User-Agent": "CardBriefingBot/1.0"}, timeout=10)
        posts = r.json().get("data", {}).get("children", [])
        cutoff = datetime.utcnow() - timedelta(hours=24)
        for post in posts:
            data = post.get("data", {})
            created = datetime.utcfromtimestamp(data.get("created_utc", 0))
            if created < cutoff:
                continue
            text = (data.get("title", "") + " " + data.get("selftext", "")).lower()
            for card_name in watchlist:
                keywords = card_name.lower().split()
                if all(kw in text for kw in keywords[:2]):
                    reddit_mentions[card_name] = reddit_mentions.get(card_name, 0) + 1
        time.sleep(1)
    except Exception as e:
        lines.append(f"Reddit fetch error: {e}")
    hype_cards = []
    for name, query in watchlist.items():
        mentions = reddit_mentions.get(name, 0)
        if mentions < 3:
            continue
        recent_sales = scrape_ebay_sold(query)[:7]
        prior_sales  = scrape_ebay_sold(query)[:14]
        recent_count = len(recent_sales)
        prior_count  = max(len(prior_sales) - recent_count, 1)
        volume_pct   = ((recent_count - prior_count) / prior_count) * 100
        if volume_pct >= 50:
            hype_cards.append((name, mentions, volume_pct, recent_sales))
    if not hype_cards:
        lines.append("No hype signals today.")
    else:
        for name, mentions, vol_pct, recent_sales in hype_cards:
            lines.append(f"\n{name}")
            lines.append(f"Reddit mentions (24hr): {mentions}")
            lines.append(f"eBay volume spike: +{vol_pct:.0f}%")
            for price_val, date_str, price_str in recent_sales[:3]:
                lines.append(f"  • {price_str} — {date_str}")
    return "\n".join(lines)

def build_message():
    now_est = datetime.utcnow() - timedelta(hours=5)
    today   = now_est.strftime("%a %b %-d")
    lines   = [f"📈 CARD BRIEFING — {today}"]
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

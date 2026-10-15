# engine.py
import re
import time
import json
import urllib.request
import urllib.error
import pandas as pd

WALLET_REGEX = r"0x[a-fA-F0-9]{40}\b"
TX_HASH_REGEX = r"0x[a-fA-F0-9]{64}\b"
USD_CLAIM_REGEX = r"(?:\$|\bUSD\s?)[0-9][0-9,]*(?:\.\d{1,2})?"
ETH_AMOUNT_REGEX = r"(\d+(?:\.\d+)?)\s*ETH\b"
TS_IN_TEXT_REGEX = r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?"

# Verification statuses (single source of truth, used by every page)
V_OK = "Verified On-Chain"
V_SIM = "Unverified (Simulated Ledger)"
V_MISMATCH = "Mismatch (differs from chain)"
V_NOTFOUND = "Not Found On-Chain"
V_ERROR = "Verification Error"
V_INFERRED = "Inferred Association (Off-Chain)"
V_BAD = (V_MISMATCH, V_NOTFOUND, V_ERROR)

LEDGER_COLUMNS = [
    "timestamp", "tx_hash", "from_wallet", "from_label", "to_wallet", "to_label",
    "amount_eth", "hop_stage", "suspicious_indicator", "verification",
]
TRACED_COLUMNS = LEDGER_COLUMNS + ["hop_velocity", "hop_minutes"]

BLOCKSCOUT = "https://eth.blockscout.com/api/v2"
CEX_KEYWORDS = (
    "binance", "coinbase", "kraken", "okx", "okex", "bybit", "kucoin", "huobi", "htx",
    "bitfinex", "gemini", "crypto.com", "gate.io", "bitget", "mexc", "bitstamp", "upbit",
)

# ----------------------------------------------------------------------------
# Chat parsing (three supported export formats)
# ----------------------------------------------------------------------------
_CHAT_PATTERNS = [
    # [2026-10-12 09:14:22] Sender: message   (also WhatsApp iOS: [12/10/26, 9:14:22 AM] Sender: message)
    ("Bracketed timestamp", re.compile(r"^\[(?P<ts>[^\]]+)\]\s+(?P<sender>[^:]+?):\s+(?P<msg>.*)$")),
    # 12/10/2026, 09:14 - Sender: message     (WhatsApp Android)
    ("WhatsApp (Android)", re.compile(
        r"^(?P<ts>\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?)\s+-\s+(?P<sender>[^:]+?):\s+(?P<msg>.*)$")),
    # Sender, [12.10.2026 09:14]:             (Telegram text export; message may follow on next lines)
    ("Telegram", re.compile(
        r"^(?P<sender>.+?),\s+\[(?P<ts>\d{1,2}\.\d{1,2}\.\d{2,4}\s+\d{1,2}:\d{2}(?::\d{2})?)\]:?\s*(?P<msg>.*)$")),
]
_WA_SYSTEM = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?\s+-\s")


def _normalize_ts(raw: str) -> str:
    """Normalises chat timestamps to 'YYYY-MM-DD HH:MM:SS'. Falls back to the raw text if unparseable."""
    raw = raw.strip()
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}", raw):
            t = pd.to_datetime(raw)
        else:
            cleaned = raw.replace(".", "/") if re.match(r"^\d{1,2}\.\d{1,2}\.\d{2,4}", raw) else raw
            t = pd.to_datetime(cleaned, dayfirst=True)
        if pd.isna(t):
            return raw
        if getattr(t, "tzinfo", None) is not None:
            t = t.tz_convert("UTC").tz_localize(None)
        return t.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return raw


def parse_chat(chat_text: str) -> list:
    """Parses a chat export into [{ts_raw, timestamp, sender, message, fmt}]. Multi-line messages are joined."""
    messages = []
    current = None
    for line in chat_text.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        matched = None
        for fmt, pattern in _CHAT_PATTERNS:
            m = pattern.match(stripped)
            if m:
                matched = (fmt, m)
                break
        if matched:
            fmt, m = matched
            current = {
                "ts_raw": m.group("ts"),
                "timestamp": _normalize_ts(m.group("ts")),
                "sender": m.group("sender").strip(),
                "message": m.group("msg").strip(),
                "fmt": fmt,
            }
            messages.append(current)
        elif _WA_SYSTEM.match(stripped):
            current = None  # WhatsApp system line (no sender), not part of a message
        elif current is not None:
            current["message"] = (current["message"] + " " + stripped).strip()
    return messages


def _unique_ci(items) -> list:
    seen, out = set(), []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return sorted(out, key=str.lower)


def _parse_usd(token: str):
    num = re.sub(r"[^0-9.]", "", token).rstrip(".")
    try:
        return float(num)
    except ValueError:
        return None


def _fmt_usd(value: float) -> str:
    return f"USD {value:,.0f}" if float(value).is_integer() else f"USD {value:,.2f}"


def extract_offchain_evidence(chat_text: str, victim_report: str, screenshot_ocr_text: str = "",
                              screenshot_time: str = "") -> dict:
    """Extracts wallets, tx hashes, claimed balances, demands and timestamped chat events."""
    combined_text = f"{victim_report}\n{chat_text}\n{screenshot_ocr_text}"
    wallets = _unique_ci(re.findall(WALLET_REGEX, combined_text))
    tx_hashes = _unique_ci(re.findall(TX_HASH_REGEX, combined_text))

    claim_values = []
    for token in re.findall(USD_CLAIM_REGEX, combined_text):
        v = _parse_usd(token)
        if v is not None and v not in claim_values:
            claim_values.append(v)

    parsed = parse_chat(chat_text)
    chat_events, chat_messages = [], []
    senders = set()
    wallet_senders, hash_senders = set(), set()

    for idx, msg in enumerate(parsed):
        ts, sender, text = msg["timestamp"], msg["sender"], msg["message"]
        senders.add(sender)
        m_wallets = re.findall(WALLET_REGEX, text)
        m_hashes = re.findall(TX_HASH_REGEX, text)
        m_eth = [float(x) for x in re.findall(ETH_AMOUNT_REGEX, text)]
        if m_wallets:
            wallet_senders.add(sender)
        if m_hashes:
            hash_senders.add(sender)

        tags = []
        if m_wallets:
            tags.append("Wallet Instruction")
        if m_hashes:
            tags.append("Victim Tx Confirmation")
        if re.search(USD_CLAIM_REGEX, text):
            tags.append("Fake Profit Claim")
        if any(w in text.lower() for w in ["urgent", "tax", "forfeit", "unlock", "vip", "freeze", "compliance"]):
            tags.append("Coercion / Urgency Tactic")

        chat_events.append({
            "timestamp": ts,
            "actor": sender,
            "event_type": "Off-Chain Chat Message",
            "details": text,
            "indicators": ", ".join(tags) if tags else "General Communication",
            "evidence_ref": f"Chat Log [{ts}]",
            "verification_status": V_INFERRED,
            "linked_evidence": "—",
        })
        chat_messages.append({
            "event_idx": idx, "timestamp": ts, "actor": sender,
            "wallets": m_wallets, "hashes": m_hashes, "eth_amounts": m_eth,
        })

    if screenshot_ocr_text.strip():
        shot_ts = ""
        if screenshot_time.strip():
            shot_ts = _normalize_ts(screenshot_time)
        else:
            found = re.search(TS_IN_TEXT_REGEX, screenshot_ocr_text)
            if found:
                shot_ts = _normalize_ts(found.group(0))
        chat_events.append({
            "timestamp": shot_ts or "Undated",
            "actor": "Platform Screenshot Evidence",
            "event_type": "Off-Chain Visual Evidence",
            "details": f"Screenshot Text Extracted: {screenshot_ocr_text.strip()}",
            "indicators": "Platform UI Balance Claim (compare against on-chain data)",
            "evidence_ref": "Screenshot text (analyst-entered / OCR)",
            "verification_status": V_INFERRED,
            "linked_evidence": "—",
        })

    # Actors: whoever hands out wallet addresses is treated as the suspected operator (inferred, not proven)
    scammer_actors = sorted(wallet_senders - hash_senders) or sorted(wallet_senders)
    victim_actors = sorted(hash_senders - set(scammer_actors))

    wallet_demands = {}
    for m in chat_messages:
        if m["actor"] in scammer_actors and m["wallets"] and m["eth_amounts"]:
            for w in m["wallets"]:
                wallet_demands[w.lower()] = {
                    "amount_eth": m["eth_amounts"][0], "timestamp": m["timestamp"], "actor": m["actor"],
                }

    name_match = re.search(r"Victim Name:\s*(.+)", victim_report or "")
    type_match = re.search(r"Incident Type:\s*(.+)", victim_report or "")
    tax_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*['\"‘’“”]?\s*(?:unlock\s+)?(?:tax|fee)", victim_report or "", re.I)

    return {
        "extracted_wallets": wallets,
        "extracted_tx_hashes": tx_hashes,
        "claimed_usd_amounts": [_fmt_usd(v) for v in claim_values],
        "claimed_usd_values": claim_values,
        "identified_actors": sorted(senders),
        "scammer_actors": scammer_actors,
        "victim_actors": victim_actors,
        "wallet_demands": wallet_demands,
        "chat_events": chat_events,
        "chat_messages": chat_messages,
        "chat_formats": sorted({m["fmt"] for m in parsed}),
        "victim_name": name_match.group(1).strip() if name_match else "",
        "incident_type": type_match.group(1).strip() if type_match else "",
        "demanded_tax_pct": float(tax_match.group(1)) if tax_match else None,
        "chain_links": [],
    }


# ----------------------------------------------------------------------------
# Tracing
# ----------------------------------------------------------------------------
def trace_onchain_funds(extracted_wallets: list, ledger: list, ledger_source: str = "simulated") -> pd.DataFrame:
    """Traces multi-hop fund movements across wallets and computes time-delta velocity.

    ledger_source="simulated" marks every row as unverified (simulated ledger records are never
    presented as verified, whatever the sample data says); "live" keeps the row's own status.
    """
    if not ledger:
        return pd.DataFrame(columns=TRACED_COLUMNS)

    known = {w.lower() for w in extracted_wallets}
    traced_rows, seen = [], set()
    for _ in range(10):
        grew = False
        for idx, row in enumerate(ledger):
            if idx in seen:
                continue
            if row["from_wallet"].lower() in known or row["to_wallet"].lower() in known:
                known.add(row["from_wallet"].lower())
                known.add(row["to_wallet"].lower())
                seen.add(idx)
                traced_rows.append(dict(row))
                grew = True
        if not grew:
            break

    if not traced_rows:
        return pd.DataFrame(columns=TRACED_COLUMNS)

    df = pd.DataFrame(traced_rows)
    for col in LEDGER_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    if ledger_source == "simulated":
        df["verification"] = V_SIM
    df = df.sort_values("timestamp").reset_index(drop=True)

    ts = pd.to_datetime(df["timestamp"])
    from_l = df["from_wallet"].str.lower().tolist()
    to_l = df["to_wallet"].str.lower().tolist()
    minutes, velocity = [], []
    for i in range(len(df)):
        prev = [j for j in range(i) if to_l[j] == from_l[i]]
        if prev:
            d = round((ts.iloc[i] - ts.iloc[prev[-1]]).total_seconds() / 60.0, 1)
            minutes.append(d)
            velocity.append(f"{d} mins after receipt")
        else:
            minutes.append(float("nan"))
            velocity.append("Origin Transfer")
    df["hop_minutes"] = minutes
    df["hop_velocity"] = velocity
    return df


def apply_verification(traced_df: pd.DataFrame, results: dict) -> pd.DataFrame:
    """Overlays on-chain verification results (keyed by lowercase tx hash) onto the traced ledger."""
    if traced_df.empty or not results:
        return traced_df
    df = traced_df.copy()
    df["verification"] = [
        results.get(h.lower(), {}).get("status", v) for h, v in zip(df["tx_hash"], df["verification"])
    ]
    return df


def identify_roles(traced_df: pd.DataFrame) -> dict:
    """Derives victim / deposit / mule / CEX wallets from the traced ledger labels."""
    roles = {"victim": [], "deposit": [], "cex": [], "mule": []}
    if traced_df.empty:
        return roles

    def add(key, wallet):
        if wallet not in roles[key]:
            roles[key].append(wallet)

    for _, r in traced_df.iterrows():
        if "Victim" in r["from_label"]:
            add("victim", r["from_wallet"])
            add("deposit", r["to_wallet"])
    for _, r in traced_df.iterrows():
        for w, label in ((r["from_wallet"], r["from_label"]), (r["to_wallet"], r["to_label"])):
            if "CEX" in label or "Binance" in label:
                add("cex", w)
    for _, r in traced_df.iterrows():
        for w in (r["from_wallet"], r["to_wallet"]):
            if w not in roles["victim"] + roles["deposit"] + roles["cex"]:
                add("mule", w)
    return roles


def compute_case_metrics(traced_df: pd.DataFrame, extracted: dict) -> dict:
    """All headline numbers are computed from the data - nothing is hardcoded."""
    roles = identify_roles(traced_df)
    m = {
        "roles": roles, "total_loss_eth": 0.0, "cex_eth": 0.0, "pct_siphoned": None,
        "fastest_hop_min": None, "peel_minutes": None,
        "claimed_usd": max(extracted.get("claimed_usd_values") or [0]) or None,
        "n_transfers": len(traced_df), "n_verified": 0,
    }
    if traced_df.empty:
        return m

    victims, deposits, cexs = set(roles["victim"]), set(roles["deposit"]), set(roles["cex"])
    m["total_loss_eth"] = float(traced_df[traced_df["from_wallet"].isin(victims)]["amount_eth"].sum())
    m["cex_eth"] = float(traced_df[traced_df["to_wallet"].isin(cexs)]["amount_eth"].sum())

    dep_in = traced_df[traced_df["from_wallet"].isin(victims) & traced_df["to_wallet"].isin(deposits)]["amount_eth"].sum()
    dep_rows_out = traced_df[traced_df["from_wallet"].isin(deposits) & ~traced_df["to_wallet"].isin(victims)]
    if dep_in > 0:
        m["pct_siphoned"] = float(min(100.0, dep_rows_out["amount_eth"].sum() / dep_in * 100.0))

    hops = traced_df["hop_minutes"].dropna()
    if not hops.empty:
        m["fastest_hop_min"] = float(hops.min())
    peel = dep_rows_out["hop_minutes"].dropna()
    if not peel.empty:
        m["peel_minutes"] = (float(peel.min()), float(peel.max()))

    m["n_verified"] = int((traced_df["verification"] == V_OK).sum())
    return m


def score_wallet_risks(traced_df: pd.DataFrame, extracted_wallets: list) -> pd.DataFrame:
    """Generates an explainable risk score (0-100) for every wallet in the investigation."""
    cited = {w.lower() for w in extracted_wallets}
    wallet_records = {}

    for _, row in traced_df.iterrows():
        for w_col, l_col in [("from_wallet", "from_label"), ("to_wallet", "to_label")]:
            w = row[w_col]
            if w not in wallet_records:
                wallet_records[w] = {
                    "wallet_address": w, "entity_label": row[l_col], "in_offchain_chat": w.lower() in cited,
                    "inbound_eth": 0.0, "outbound_eth": 0.0, "tx_count": 0,
                }
        wallet_records[row["from_wallet"]]["outbound_eth"] += row["amount_eth"]
        wallet_records[row["from_wallet"]]["tx_count"] += 1
        wallet_records[row["to_wallet"]]["inbound_eth"] += row["amount_eth"]
        wallet_records[row["to_wallet"]]["tx_count"] += 1

    known_lower = {w.lower() for w in wallet_records}
    for w in extracted_wallets:
        if w.lower() not in known_lower:
            wallet_records[w] = {
                "wallet_address": w, "entity_label": "Unfunded Cited Wallet", "in_offchain_chat": True,
                "inbound_eth": 0.0, "outbound_eth": 0.0, "tx_count": 0,
            }

    scored_list = []
    for w, data in wallet_records.items():
        score = 10
        reasons = []
        label = data["entity_label"]

        if "Victim" in label:
            score = 5
            reasons.append("Victim origin wallet")
        else:
            if data["in_offchain_chat"]:
                score += 45
                reasons.append("Explicitly cited in off-chain scammer chat (+45)")
            if data["inbound_eth"] > 0 and data["outbound_eth"] > 0:
                retention = max(0.0, data["inbound_eth"] - data["outbound_eth"])
                if retention < 0.1 * data["inbound_eth"]:
                    through = min(100.0, data["outbound_eth"] / data["inbound_eth"] * 100.0)
                    score += 35
                    reasons.append(f"{through:.1f}% pass-through / minimal retention (+35)")
            if "Mule" in label:
                score += 30
                reasons.append("Intermediary peel-chain node (+30)")
            if "CEX" in label or "Binance" in label:
                score = 85
                reasons = ["High-priority CEX cash-out consolidation endpoint (Freeze Target)"]
            if data["tx_count"] == 0 and data["in_offchain_chat"]:
                score = 75
                reasons = ["Inferred association: cited/demanded in chat, 0 traced txs"]

        scored_list.append({
            "Wallet Address": w,
            "Role / Classification": label,
            "Risk Score": min(100, score),
            "Inbound (ETH)": round(data["inbound_eth"], 2),
            "Outbound (ETH)": round(data["outbound_eth"], 2),
            "Current Balance (ETH)": round(max(0.0, data["inbound_eth"] - data["outbound_eth"]), 4),
            "Explainable Evidence Basis": "; ".join(reasons),
        })

    cols = ["Wallet Address", "Role / Classification", "Risk Score", "Inbound (ETH)", "Outbound (ETH)",
            "Current Balance (ETH)", "Explainable Evidence Basis"]
    if not scored_list:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(scored_list).sort_values("Risk Score", ascending=False).reset_index(drop=True)


# ----------------------------------------------------------------------------
# Chat <-> chain linking and timeline
# ----------------------------------------------------------------------------
LINK_COLUMNS = [
    "chat_timestamp", "chat_actor", "claimed_tx_hash", "claimed_amount_eth", "link_status",
    "on_chain_amount_eth", "on_chain_time", "chat_vs_chain_minutes", "transfer", "verification",
]


def link_chat_to_chain(extracted: dict, traced_df: pd.DataFrame) -> pd.DataFrame:
    """Matches tx hashes / wallets cited in evidence against traced transfers.

    Also writes a human-readable 'linked_evidence' note onto each chat event.
    """
    msgs = extracted.get("chat_messages", [])
    events = extracted.get("chat_events", [])
    chain = {}
    if not traced_df.empty:
        for _, r in traced_df.iterrows():
            chain[r["tx_hash"].lower()] = r

    cited = {}
    for m in msgs:
        for h in m["hashes"]:
            cited.setdefault(h.lower(), m)

    rows = []
    notes = {}
    for h in extracted.get("extracted_tx_hashes", []):
        m = cited.get(h.lower())
        r = chain.get(h.lower())
        claimed = m["eth_amounts"][0] if (m and m["eth_amounts"]) else None
        row = {
            "chat_timestamp": m["timestamp"] if m else "—",
            "chat_actor": m["actor"] if m else "Victim statement / OCR text",
            "claimed_tx_hash": h, "claimed_amount_eth": claimed,
            "link_status": "Unmatched: hash not in traced ledger",
            "on_chain_amount_eth": None, "on_chain_time": "—", "chat_vs_chain_minutes": None,
            "transfer": "—", "verification": "—",
        }
        if r is not None:
            status = "Matched"
            if claimed is not None and abs(claimed - float(r["amount_eth"])) > 1e-6:
                status = "Matched (amount differs)"
            delta = None
            if m:
                a, b = pd.to_datetime(m["timestamp"], errors="coerce"), pd.to_datetime(r["timestamp"], errors="coerce")
                if not pd.isna(a) and not pd.isna(b):
                    delta = round((a - b).total_seconds() / 60.0, 1)
            row.update({
                "link_status": status, "on_chain_amount_eth": float(r["amount_eth"]),
                "on_chain_time": r["timestamp"], "chat_vs_chain_minutes": delta,
                "transfer": f"{r['from_label']} -> {r['to_label']}", "verification": r["verification"],
            })
        rows.append(row)
        if m:
            if r is not None:
                d = row["chat_vs_chain_minutes"]
                when = f"; chat message {d:+.1f} min vs chain time" if d is not None else ""
                notes.setdefault(m["event_idx"], []).append(
                    f"{row['link_status']}: tx {h[:12]}... {row['on_chain_amount_eth']} ETH "
                    f"{row['transfer']} @ {row['on_chain_time']} [{row['verification']}]{when}")
            else:
                notes.setdefault(m["event_idx"], []).append(f"Unmatched: tx {h[:12]}... not found in traced ledger")

    for m in msgs:
        for w in m["wallets"]:
            wl = w.lower()
            if traced_df.empty:
                n = 0
                inbound = 0.0
            else:
                touching = traced_df[(traced_df["from_wallet"].str.lower() == wl) | (traced_df["to_wallet"].str.lower() == wl)]
                n = len(touching)
                inbound = float(touching[touching["to_wallet"].str.lower() == wl]["amount_eth"].sum())
            if n:
                notes.setdefault(m["event_idx"], []).append(f"Wallet {w[:8]}... has {n} traced transfer(s), {inbound:.2f} ETH received")
            else:
                notes.setdefault(m["event_idx"], []).append(f"Wallet {w[:8]}... has no traced on-chain activity (inferred only)")

    for idx, parts in notes.items():
        if idx < len(events):
            events[idx]["linked_evidence"] = " | ".join(parts)

    return pd.DataFrame(rows, columns=LINK_COLUMNS)


def correlate_timeline(chat_events: list, traced_df: pd.DataFrame, link_df: pd.DataFrame = None) -> pd.DataFrame:
    """Combines off-chain chat evidence and on-chain transfers into a unified timeline."""
    timeline_rows = [dict(e) for e in chat_events]

    reverse = {}
    if link_df is not None and not link_df.empty:
        for _, l in link_df.iterrows():
            if l["chat_timestamp"] != "—":
                reverse[l["claimed_tx_hash"].lower()] = f"Chat Log [{l['chat_timestamp']}] ({l['chat_actor']}) cites this tx"

    for _, row in traced_df.iterrows():
        vel = f" [{row['hop_velocity']}]" if "hop_velocity" in row else ""
        timeline_rows.append({
            "timestamp": row["timestamp"],
            "actor": f"{row['from_label']} -> {row['to_label']}",
            "event_type": f"On-Chain Transfer ({row['hop_stage']})",
            "details": f"Transferred {row['amount_eth']} ETH ({row['from_wallet'][:8]}... to {row['to_wallet'][:8]}...){vel}",
            "indicators": row["suspicious_indicator"],
            "evidence_ref": f"Tx: {row['tx_hash'][:14]}...",
            "verification_status": row["verification"],
            "linked_evidence": reverse.get(row["tx_hash"].lower(), "No chat reference"),
        })

    timeline_df = pd.DataFrame(timeline_rows)
    if not timeline_df.empty:
        timeline_df = timeline_df.sort_values("timestamp", kind="stable").reset_index(drop=True)
    return timeline_df


# ----------------------------------------------------------------------------
# Live Blockscout access (Ethereum Mainnet)
# ----------------------------------------------------------------------------
def _http_get_json(url: str, timeout: int = 8):
    req = urllib.request.Request(url, headers={"User-Agent": "ChainSleuth-Forensics/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _chain_ts(raw: str) -> str:
    try:
        t = pd.to_datetime(raw, utc=True).tz_convert("UTC").tz_localize(None)
        return t.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(raw)


def _entity_name(obj: dict) -> str:
    if not obj:
        return ""
    name = obj.get("name") or obj.get("ens_domain_name") or ""
    if not name:
        for tag in obj.get("public_tags") or []:
            lab = tag.get("label") or tag.get("display_name")
            if lab:
                name = lab
                break
    return name or ""


def _is_cex(name: str) -> bool:
    n = (name or "").lower()
    return any(k in n for k in CEX_KEYWORDS)


def _parse_tx(item: dict):
    frm, to = item.get("from") or {}, item.get("to") or {}
    if not frm.get("hash") or not to.get("hash"):
        return None
    try:
        wei = int(item.get("value") or 0)
    except (TypeError, ValueError):
        wei = 0
    return {
        "hash": item.get("hash", ""),
        "from": frm["hash"], "to": to["hash"],
        "from_name": _entity_name(frm), "to_name": _entity_name(to),
        "to_is_contract": bool(to.get("is_contract")),
        "amount_eth": wei / 1e18,
        "timestamp": _chain_ts(item.get("timestamp", "")),
        "status": item.get("status") or item.get("result") or "ok",
    }


def fetch_transaction(tx_hash: str) -> dict:
    """Fetches one transaction from Blockscout. Distinguishes 'not found' from other failures."""
    try:
        data = _http_get_json(f"{BLOCKSCOUT}/transactions/{tx_hash.strip()}")
    except urllib.error.HTTPError as e:
        return {"success": False, "not_found": e.code == 404, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"success": False, "not_found": False, "error": str(e)}
    parsed = _parse_tx(data)
    if parsed is None:
        return {"success": False, "not_found": False, "error": "Unsupported transaction shape (e.g. contract creation)"}
    parsed.update({"success": True, "not_found": False})
    return parsed


def fetch_address_transactions(address: str, direction: str = "from", limit: int = 50) -> list:
    """Fetches the most recent native-ETH transactions sent from / to an address (first page)."""
    data = _http_get_json(f"{BLOCKSCOUT}/addresses/{address.strip()}/transactions?filter={direction}")
    out = []
    for item in data.get("items", []):
        tx = _parse_tx(item)
        if tx and str(tx["status"]).lower() in ("ok", "success"):
            out.append(tx)
    return out[:limit]


def verify_ledger_on_chain(traced_df: pd.DataFrame, delay: float = 0.15, tolerance_minutes: float = 10.0) -> dict:
    """Checks each ledger row against Ethereum Mainnet (sender, receiver, value, time).

    Returns {lower_tx_hash: {"status": ..., "detail": ...}}. Timestamps are assumed to be UTC.
    Only native ETH transfers (the top-level transaction value) are compared.
    """
    results = {}
    for _, row in traced_df.iterrows():
        h = row["tx_hash"]
        chain = fetch_transaction(h)
        if chain.get("not_found"):
            results[h.lower()] = {"status": V_NOTFOUND, "detail": "Hash does not exist on Ethereum Mainnet (Blockscout 404)."}
        elif not chain.get("success"):
            results[h.lower()] = {"status": V_ERROR, "detail": chain.get("error", "unknown error")}
        else:
            diffs = []
            if chain["from"].lower() != row["from_wallet"].lower():
                diffs.append(f"sender on-chain {chain['from'][:10]}...")
            if chain["to"].lower() != row["to_wallet"].lower():
                diffs.append(f"receiver on-chain {chain['to'][:10]}...")
            if abs(chain["amount_eth"] - float(row["amount_eth"])) > 1e-6:
                diffs.append(f"value on-chain {chain['amount_eth']:.6f} ETH vs ledger {row['amount_eth']}")
            a, b = pd.to_datetime(chain["timestamp"], errors="coerce"), pd.to_datetime(row["timestamp"], errors="coerce")
            if not pd.isna(a) and not pd.isna(b) and abs((a - b).total_seconds()) / 60.0 > tolerance_minutes:
                diffs.append(f"time on-chain {chain['timestamp']} vs ledger {row['timestamp']}")
            if diffs:
                results[h.lower()] = {"status": V_MISMATCH, "detail": "; ".join(diffs)}
            else:
                results[h.lower()] = {"status": V_OK, "detail": f"Sender, receiver, value and time match chain ({chain['timestamp']} UTC)."}
        if delay:
            time.sleep(delay)
    return results


def build_live_ledger(wallets: list, tx_hashes: list, max_hops: int = 2, per_wallet: int = 15,
                      max_rows: int = 60, delay: float = 0.2):
    """Builds a ledger in the same schema as the sample ledger from live Mainnet data.

    Seeds from victim-cited tx hashes (sender = victim, receiver = suspected deposit wallet) and from
    wallets cited in chat, then follows outbound ETH transfers for up to `max_hops` hops, stopping at
    labelled exchange endpoints. Returns (rows, warnings). Roles are inferred from position, not proven.
    """
    warnings, rows, seen_hashes = [], [], set()
    labels = {}  # lower address -> label
    counters = {"deposit": 0, "mule": 0}
    cited = {w.lower() for w in wallets}
    victims = set()

    def register(addr, entity, role):
        key = addr.lower()
        if key in labels:
            return labels[key]
        if _is_cex(entity):
            labels[key] = f"{entity} (CEX Endpoint)"
        elif role == "victim":
            labels[key] = "Victim Wallet"
        elif role == "deposit":
            counters["deposit"] += 1
            labels[key] = f"Scammer Deposit Node {counters['deposit']}"
        else:
            counters["mule"] += 1
            labels[key] = f"Intermediary Mule Wallet {counters['mule']} (candidate)"
        return labels[key]

    def add_row(tx, stage, indicator):
        if tx["hash"] in seen_hashes or len(rows) >= max_rows:
            return False
        seen_hashes.add(tx["hash"])
        rows.append({
            "timestamp": tx["timestamp"], "tx_hash": tx["hash"],
            "from_wallet": tx["from"], "from_label": labels[tx["from"].lower()],
            "to_wallet": tx["to"], "to_label": labels[tx["to"].lower()],
            "amount_eth": round(tx["amount_eth"], 6), "hop_stage": stage,
            "suspicious_indicator": indicator, "verification": V_OK,
        })
        return True

    frontier, earliest = [], None
    for h in tx_hashes:
        res = fetch_transaction(h)
        if not res.get("success"):
            warnings.append(f"Victim-cited tx {h[:14]}... could not be loaded ({res.get('error')}).")
            continue
        victims.add(res["from"].lower())
        register(res["from"], res["from_name"], "victim")
        register(res["to"], res["to_name"], "deposit")
        add_row(res, "Victim-Reported Transfer", "Hash cited in victim evidence")
        frontier.append(res["to"])
        earliest = res["timestamp"] if earliest is None else min(earliest, res["timestamp"])

    for w in wallets:
        if w.lower() not in victims and w.lower() not in labels:
            register(w, "", "deposit")
            frontier.append(w)

    visited = set()
    for hop in range(1, max_hops + 1):
        next_nodes = []
        for addr in frontier:
            if addr.lower() in visited or labels.get(addr.lower(), "").endswith("(CEX Endpoint)"):
                continue
            visited.add(addr.lower())
            try:
                txs = fetch_address_transactions(addr, "from", 50)
            except Exception as e:
                warnings.append(f"Could not load transfers for {addr[:10]}... ({e}).")
                continue
            txs = [t for t in txs if t["amount_eth"] > 0 and t["to"].lower() not in victims
                   and (earliest is None or t["timestamp"] >= earliest)]
            txs.sort(key=lambda t: t["amount_eth"], reverse=True)
            for t in txs[:per_wallet]:
                register(t["from"], t["from_name"], "mule")
                dest_label = register(t["to"], t["to_name"], "mule")
                is_cex = dest_label.endswith("(CEX Endpoint)")
                stage = f"Hop {hop}" + (" (Exchange Cash-Out)" if is_cex else "")
                if is_cex:
                    indicator = "Deposit into exchange endpoint (label from Blockscout)"
                elif t["from"].lower() in cited:
                    indicator = "Outbound transfer from a wallet cited in off-chain evidence"
                else:
                    indicator = "Onward transfer of traced funds"
                if add_row(t, stage, indicator) and not is_cex and not t["to_is_contract"]:
                    next_nodes.append(t["to"])
            if delay:
                time.sleep(delay)
        frontier = next_nodes
        if not frontier:
            break

    if len(rows) >= max_rows:
        warnings.append(f"Result capped at {max_rows} transfers; narrow the evidence or reduce hops for a full trace.")
    return rows, warnings


def fetch_live_eth_address(address: str) -> dict:
    """Queries public Blockscout Ethereum Mainnet API for live on-chain verification during demo."""
    url = f"https://eth.blockscout.com/api/v2/addresses/{address.strip()}"
    req = urllib.request.Request(url, headers={"User-Agent": "ChainSleuth-Forensics/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            coin_bal = float(data.get("coin_balance") or 0) / 1e18
            return {
                "success": True,
                "address": data.get("hash", address),
                "is_contract": data.get("is_contract", False),
                "eth_balance": round(coin_bal, 4),
                "ens_domain": data.get("ens_domain_name") or "None",
                "implementation_name": data.get("name") or "Standard EOA Wallet"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

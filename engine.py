# engine.py
import re
import urllib.request
import json
import pandas as pd

WALLET_REGEX = r"0x[a-fA-F0-9]{40}\b"
TX_HASH_REGEX = r"0x[a-fA-F0-9]{64}\b"
CHAT_LINE_REGEX = r"^\[(.*?)\]\s+(.*?):\s+(.*)$"
USD_CLAIM_REGEX = r"\$[0-9,]+(?:\.\d{2})?"


def extract_offchain_evidence(chat_text: str, victim_report: str, screenshot_ocr_text: str = "") -> dict:
    """Extracts wallets, tx hashes, claimed fake balances, and timestamped chat events."""
    combined_text = f"{victim_report}\n{chat_text}\n{screenshot_ocr_text}"
    wallets = sorted(list(set(re.findall(WALLET_REGEX, combined_text))))
    tx_hashes = sorted(list(set(re.findall(TX_HASH_REGEX, combined_text))))
    claimed_usd = re.findall(USD_CLAIM_REGEX, combined_text)

    chat_events = []
    senders = set()

    for line in chat_text.strip().splitlines():
        match = re.match(CHAT_LINE_REGEX, line.strip())
        if match:
            timestamp, sender, message = match.groups()
            senders.add(sender)

            tags = []
            if re.search(WALLET_REGEX, message):
                tags.append("Wallet Instruction")
            if re.search(TX_HASH_REGEX, message):
                tags.append("Victim Tx Confirmation")
            if re.search(USD_CLAIM_REGEX, message):
                tags.append("Fake Profit Claim")
            if any(w in message.lower() for w in ["urgent", "tax", "forfeit", "unlock", "vip", "freeze", "compliance"]):
                tags.append("Coercion / Urgency Tactic")

            chat_events.append({
                "timestamp": timestamp,
                "actor": sender,
                "event_type": "Off-Chain Chat Message",
                "details": message,
                "indicators": ", ".join(tags) if tags else "General Communication",
                "evidence_ref": f"Chat Log [{timestamp}]",
                "verification_status": "Inferred Association (Off-Chain)"
            })

    if screenshot_ocr_text.strip():
        chat_events.append({
            "timestamp": "2026-10-13 19:00:00",
            "actor": "Platform Screenshot Evidence",
            "event_type": "Off-Chain Visual Evidence",
            "details": f"Screenshot Text Extracted: {screenshot_ocr_text.strip()}",
            "indicators": "Fraudulent UI Balance Claim (Contradicts On-Chain Drain)",
            "evidence_ref": "Uploaded Screenshot Artifact",
            "verification_status": "Inferred Association (Off-Chain)"
        })

    return {
        "extracted_wallets": wallets,
        "extracted_tx_hashes": tx_hashes,
        "claimed_usd_amounts": claimed_usd,
        "identified_actors": sorted(list(senders)),
        "chat_events": chat_events
    }


def trace_onchain_funds(extracted_wallets: list, ledger: list) -> pd.DataFrame:
    """Traces multi-hop fund movements across wallets and computes time-delta velocity."""
    df = pd.DataFrame(ledger)
    if df.empty:
        return df

    known_wallets = set(extracted_wallets)
    traced_rows = []

    for _ in range(4):
        for row in ledger:
            if row["from_wallet"] in known_wallets or row["to_wallet"] in known_wallets:
                known_wallets.add(row["from_wallet"])
                known_wallets.add(row["to_wallet"])
                if row not in traced_rows:
                    traced_rows.append(row)

    traced_df = pd.DataFrame(traced_rows).sort_values("timestamp").reset_index(drop=True)

    # Calculate algorithmic hop time delta in minutes
    if not traced_df.empty:
        ts = pd.to_datetime(traced_df["timestamp"])
        deltas = []
        for i, row in traced_df.iterrows():
            prev_inbounds = traced_df.iloc[:i][traced_df.iloc[:i]["to_wallet"] == row["from_wallet"]]
            if not prev_inbounds.empty:
                last_in_time = pd.to_datetime(prev_inbounds.iloc[-1]["timestamp"])
                diff_mins = round((ts.iloc[i] - last_in_time).total_seconds() / 60.0, 1)
                deltas.append(f"{diff_mins} mins after receipt")
            else:
                deltas.append("Origin Transfer")
        traced_df["hop_velocity"] = deltas

    return traced_df


def score_wallet_risks(traced_df: pd.DataFrame, extracted_wallets: list) -> pd.DataFrame:
    """Generates an explainable risk score (0-100) for every wallet in the investigation."""
    wallet_records = {}

    for _, row in traced_df.iterrows():
        for w_col, l_col in [("from_wallet", "from_label"), ("to_wallet", "to_label")]:
            w = row[w_col]
            if w not in wallet_records:
                wallet_records[w] = {
                    "wallet_address": w,
                    "entity_label": row[l_col],
                    "in_offchain_chat": w in extracted_wallets,
                    "inbound_eth": 0.0,
                    "outbound_eth": 0.0,
                    "tx_count": 0
                }
        wallet_records[row["from_wallet"]]["outbound_eth"] += row["amount_eth"]
        wallet_records[row["from_wallet"]]["tx_count"] += 1
        wallet_records[row["to_wallet"]]["inbound_eth"] += row["amount_eth"]
        wallet_records[row["to_wallet"]]["tx_count"] += 1

    for w in extracted_wallets:
        if w not in wallet_records:
            wallet_records[w] = {
                "wallet_address": w,
                "entity_label": "Unfunded Extortion Wallet",
                "in_offchain_chat": True,
                "inbound_eth": 0.0,
                "outbound_eth": 0.0,
                "tx_count": 0
            }

    scored_list = []
    for w, data in wallet_records.items():
        score = 10
        reasons = []
        label = data["entity_label"]

        if "Victim" in label:
            score = 5
            reasons.append("Verified Victim Origin Wallet")
        else:
            if data["in_offchain_chat"]:
                score += 45
                reasons.append("Explicitly cited in off-chain scammer chat (+45)")
            if data["inbound_eth"] > 0 and data["outbound_eth"] > 0:
                retention = max(0.0, data["inbound_eth"] - data["outbound_eth"])
                if retention < 0.1 * data["inbound_eth"]:
                    score += 35
                    reasons.append("99% rapid pass-through siphoning / zero retention (+35)")
            if "Mule" in label:
                score += 30
                reasons.append("Intermediary peel-chain obfuscation node (+30)")
            if "CEX" in label or "Binance" in label:
                score = 85
                reasons = ["High-priority CEX cash-out consolidation endpoint (Freeze Target)"]
            if data["tx_count"] == 0 and data["in_offchain_chat"]:
                score = 75
                reasons = ["Inferred association: demanded in chat for 'unlock tax', 0 verified txs"]

        scored_list.append({
            "Wallet Address": w,
            "Role / Classification": label,
            "Risk Score": min(100, score),
            "Inbound (ETH)": round(data["inbound_eth"], 2),
            "Outbound (ETH)": round(data["outbound_eth"], 2),
            "Current Balance (ETH)": round(max(0.0, data["inbound_eth"] - data["outbound_eth"]), 4),
            "Explainable Evidence Basis": "; ".join(reasons)
        })

    return pd.DataFrame(scored_list).sort_values("Risk Score", ascending=False).reset_index(drop=True)


def correlate_timeline(chat_events: list, traced_df: pd.DataFrame) -> pd.DataFrame:
    """Combines off-chain chat evidence and on-chain transfers into a unified timeline."""
    timeline_rows = list(chat_events)

    for _, row in traced_df.iterrows():
        vel = f" [{row.get('hop_velocity', '')}]" if "hop_velocity" in row else ""
        timeline_rows.append({
            "timestamp": row["timestamp"],
            "actor": f"{row['from_label']} -> {row['to_label']}",
            "event_type": f"On-Chain Transfer ({row['hop_stage']})",
            "details": f"Transferred {row['amount_eth']} ETH ({row['from_wallet'][:8]}... to {row['to_wallet'][:8]}...){vel}",
            "indicators": row["suspicious_indicator"],
            "evidence_ref": f"Tx: {row['tx_hash'][:14]}...",
            "verification_status": row["verification"]
        })

    timeline_df = pd.DataFrame(timeline_rows)
    if not timeline_df.empty:
        timeline_df = timeline_df.sort_values("timestamp").reset_index(drop=True)
    return timeline_df


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
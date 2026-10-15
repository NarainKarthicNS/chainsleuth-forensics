# reporter.py
import json
import re
import pandas as pd

from engine import (
    WALLET_REGEX, TX_HASH_REGEX, V_OK, V_BAD, identify_roles, compute_case_metrics,
)


def _edge_style(status: str):
    """Verified = solid electric green. Unverified ledger = dashed cyan. Failed check = dashed crimson."""
    if status == V_OK:
        return "#00ff88", "#66ffb8", False
    if status in V_BAD:
        return "#ff3366", "#ff668c", [6, 4]
    return "#00d4ff", "#66e5ff", [8, 6]


def build_interactive_graph_html(traced_df: pd.DataFrame, extracted_wallets: list, wallet_demands: dict = None) -> str:
    """Generates a Cyberpunk Vis.js graph. Edge style encodes verification status; magenta dashed = inferred off-chain."""
    wallet_demands = wallet_demands or {}
    cited = {w.lower() for w in extracted_wallets}
    nodes = {}
    edges = []
    victim_wallet = None

    for _, row in traced_df.iterrows():
        for w_col, l_col in [("from_wallet", "from_label"), ("to_wallet", "to_label")]:
            wallet = row[w_col]
            label = row[l_col]
            if "Victim" in label:
                victim_wallet = wallet

            if wallet not in nodes:
                if "Victim" in label:
                    color, level = "#00d4ff", 0  # Electric Cyan
                elif "CEX" in label or "Binance" in label:
                    color, level = "#00ff88", 3  # Primary Electric Green
                elif wallet.lower() in cited:
                    color, level = "#ff3366", 1  # Destructive Crimson
                else:
                    color, level = "#00b360", 2  # Matrix Transit Green

                nodes[wallet] = {
                    "id": wallet,
                    "label": f"{label}\n({wallet[:6]}...{wallet[-4:]})",
                    "title": f"Full Address: {wallet}\nRole: {label}",
                    "color": {
                        "background": "#12121a",
                        "border": color,
                        "highlight": {"background": "#1c1c2e", "border": color}
                    },
                    "level": level,
                    "shape": "box",
                    "borderWidth": 2,
                    "margin": 14,
                    "font": {"color": "#e0e0e0", "face": "Share Tech Mono, Courier New, monospace", "size": 13}
                }

    edge_idx = 0
    for _, row in traced_df.iterrows():
        edge_idx += 1
        roundness = 0.25 if edge_idx % 2 != 0 else -0.35
        base, hi, dashes = _edge_style(row["verification"])

        edges.append({
            "from": row["from_wallet"],
            "to": row["to_wallet"],
            "label": f"{row['amount_eth']} ETH  [{row['timestamp'][11:16]}]",
            "title": f"Tx Hash: {row['tx_hash']}\nStage: {row['hop_stage']}\nStatus: {row['verification']}",
            "arrows": "to",
            "dashes": dashes,
            "width": 2,
            "smooth": {"enabled": True, "type": "cubicBezier", "roundness": roundness},
            "color": {"color": base, "highlight": hi},
            "font": {
                "color": "#e0e0e0", "size": 11, "face": "Share Tech Mono, Courier New, monospace",
                "align": "middle", "background": "none", "strokeWidth": 0
            }
        })

    inferred_idx = 0
    for w in extracted_wallets:
        if w not in nodes and not any(w.lower() == n.lower() for n in nodes):
            inferred_idx += 1
            nodes[w] = {
                "id": w,
                "label": f"Cited Wallet {inferred_idx} (Inferred)\n({w[:6]}...{w[-4:]})",
                "title": f"Address: {w}\nStatus: Inferred Off-Chain Association (no traced transfers)",
                "color": {
                    "background": "#12121a",
                    "border": "#ff00ff",
                    "highlight": {"background": "#1c1c2e", "border": "#ff00ff"}
                },
                "level": 1,
                "shape": "box",
                "borderWidth": 2,
                "margin": 14,
                "font": {"color": "#e0e0e0", "face": "Share Tech Mono, Courier New, monospace", "size": 13}
            }
            if victim_wallet:
                demand = wallet_demands.get(w.lower())
                edge_label = f"{demand['amount_eth']} ETH Demanded [Inferred]" if demand else "Cited in chat [Inferred]"
                edges.append({
                    "from": victim_wallet,
                    "to": w,
                    "label": edge_label,
                    "title": "Off-chain demand/instruction found in chat log (not an on-chain transfer)",
                    "arrows": "to",
                    "dashes": [4, 4],
                    "width": 1.8,
                    "smooth": {"enabled": True, "type": "cubicBezier", "roundness": -0.6},
                    "color": {"color": "#ff00ff", "highlight": "#ff66ff"},
                    "font": {
                        "color": "#ff66ff", "size": 11, "face": "Share Tech Mono, Courier New, monospace",
                        "align": "middle", "background": "none", "strokeWidth": 0
                    }
                })

    nodes_json = json.dumps(list(nodes.values()))
    edges_json = json.dumps(edges)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap" rel="stylesheet">
      <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
      <style>
        body {{ margin: 0; padding: 0; background-color: #0a0a0f; }}
        #mynetwork {{
          width: 100%;
          height: 460px;
          background-color: #0a0a0f;
          background-image:
            linear-gradient(rgba(0, 255, 136, 0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 255, 136, 0.04) 1px, transparent 1px);
          background-size: 40px 40px;
          border: 1px solid #2a2a3a;
        }}
      </style>
    </head>
    <body>
      <div id="mynetwork"></div>
      <script type="text/javascript">
        var nodes = new vis.DataSet({nodes_json});
        var edges = new vis.DataSet({edges_json});
        var container = document.getElementById('mynetwork');
        var data = {{ nodes: nodes, edges: edges }};
        var options = {{
          layout: {{
            hierarchical: {{
              enabled: true,
              direction: "LR",
              sortMethod: "hubsize",
              levelSeparation: 380,
              nodeSpacing: 220,
              treeSpacing: 240
            }}
          }},
          physics: {{ enabled: false }},
          interaction: {{ hover: true, dragNodes: true, zoomView: true, dragView: true }}
        }};
        var network = new vis.Network(container, data, options);
        network.once("afterDrawing", function() {{
          network.fit({{ animation: false }});
        }});
      </script>
    </body>
    </html>
    """


def validate_ai_report(ai_text: str, source_text: str):
    """Rejects AI output that drops or invents any wallet address / tx hash. Returns (ok, reason)."""
    if not ai_text or not ai_text.strip():
        return False, "empty response"
    src = {x.lower() for x in re.findall(WALLET_REGEX, source_text)} | {x.lower() for x in re.findall(TX_HASH_REGEX, source_text)}
    ai_lower = ai_text.lower()
    ai_found = {x.lower() for x in re.findall(WALLET_REGEX, ai_text)} | {x.lower() for x in re.findall(TX_HASH_REGEX, ai_text)}
    missing = [x for x in src if x not in ai_lower]
    if missing:
        return False, f"it dropped or altered {len(missing)} wallet address/tx hash value(s)"
    invented = ai_found - src
    if invented:
        return False, f"it introduced {len(invented)} address/hash value(s) not present in the evidence"
    return True, ""


def _short(label: str) -> str:
    return label.replace(" (CEX Endpoint)", "").strip()


def _build_default_report(victim_report: str, extracted: dict, traced_df: pd.DataFrame) -> str:
    m = compute_case_metrics(traced_df, extracted)
    roles = m["roles"]
    n, n_ver = m["n_transfers"], m["n_verified"]
    incident = extracted.get("incident_type") or "Cryptocurrency fraud (type to be confirmed by investigator)"
    victim_name = extracted.get("victim_name")

    lines = ["# LAW ENFORCEMENT & COMPLIANCE INVESTIGATION REPORT (DRAFT)"]
    lines.append(f"**Case Classification:** {incident}  ")
    if victim_name:
        lines.append(f"**Reporting Victim:** {victim_name}  ")
    lines.append(f"**Total Victim Transfers (per ledger):** {m['total_loss_eth']:.2f} ETH  ")
    lines.append(f"**Total Traced to Exchange Endpoint(s):** {m['cex_eth']:.2f} ETH  ")
    if n == 0:
        lines.append("**Verification Status:** no on-chain transfers could be traced from the supplied evidence.  ")
    elif n_ver == n:
        lines.append(f"**Verification Status:** all {n} transfers re-checked against Ethereum Mainnet.  ")
    else:
        counts = traced_df["verification"].value_counts()
        breakdown = ", ".join(f"{v} x {k}" for k, v in counts.items())
        lines.append(f"**Verification Status:** {n_ver} of {n} transfers verified on Ethereum Mainnet ({breakdown}). "
                     f"Unverified records must be confirmed before submission.  ")

    lines += ["", "---", "", "## 1. Executive Evidence Correlation Summary"]

    fact_label = "Verified On-Chain Facts" if n and n_ver == n else "On-Chain Facts (as recorded in ledger; see verification status above)"
    lines.append(f"### {fact_label}")
    if n == 0:
        lines.append("* No traced transfers.")
    else:
        v_wallets = ", ".join(f"`{w}`" for w in roles["victim"]) or "victim wallet(s)"
        d_wallets = ", ".join(f"`{w}`" for w in roles["deposit"]) or "N/A"
        n_dep = len(traced_df[traced_df["from_wallet"].isin(roles["victim"])])
        lines.append(f"* **{m['total_loss_eth']:.2f} ETH** moved from {v_wallets} in {n_dep} transfer(s) to suspected deposit wallet(s) {d_wallets}.")
        if m["peel_minutes"]:
            lo, hi = m["peel_minutes"]
            rng = f"{lo:.1f}" if lo == hi else f"{lo:.1f} to {hi:.1f}"
            lines.append(f"* {m['pct_siphoned']:.1f}% of deposited funds were forwarded out of the deposit wallet(s), {rng} minutes after the preceding receipt.")
        if roles["mule"]:
            lines.append("* Intermediary wallets: " + ", ".join(f"`{w}`" for w in roles["mule"]) + ".")
        if roles["cex"]:
            cex_names = sorted({_short(l) for l in traced_df[traced_df["to_wallet"].isin(roles["cex"])]["to_label"]})
            lines.append(f"* **{m['cex_eth']:.2f} ETH** reached exchange endpoint(s): {', '.join(cex_names)}.")
        else:
            lines.append("* No exchange endpoint was identified in the traced paths.")

    lines.append("### Chat-to-Chain Linking")
    links = extracted.get("chain_links") or []
    if links:
        for l in links:
            if l["link_status"].startswith("Matched"):
                lines.append(f"* `{l['claimed_tx_hash'][:18]}...` cited by {l['chat_actor']} at {l['chat_timestamp']}: **{l['link_status']}** "
                             f"({l['on_chain_amount_eth']} ETH, {l['transfer']}, chain time {l['on_chain_time']}, status: {l['verification']}).")
            else:
                lines.append(f"* `{l['claimed_tx_hash'][:18]}...` cited by {l['chat_actor']}: **{l['link_status']}**.")
    else:
        lines.append("* No transaction hashes were found in the evidence.")

    lines.append("### Inferred Off-Chain Associations")
    actors = extracted.get("scammer_actors") or []
    deposit_set = {w.lower() for w in roles["deposit"]}
    cited_deposits = [w for w in extracted.get("extracted_wallets", []) if w.lower() in deposit_set]
    if actors:
        lines.append(f"* Chat participant(s) {', '.join('`'+a+'`' for a in actors)} supplied wallet address(es) in the chat export"
                     + (f"; {len(cited_deposits)} wallet(s) cited in chat match wallets that received victim funds on-chain." if cited_deposits else "."))
    traced_lower = {w.lower() for w in set(traced_df["from_wallet"]) | set(traced_df["to_wallet"])} if n else set()
    for w in extracted.get("extracted_wallets", []):
        if w.lower() not in traced_lower:
            d = extracted.get("wallet_demands", {}).get(w.lower())
            amt = f" for {d['amount_eth']} ETH" if d else ""
            tax = f" (victim statement mentions a {extracted['demanded_tax_pct']:g}% fee/tax)" if extracted.get("demanded_tax_pct") else ""
            lines.append(f"* Wallet `{w}` was demanded in chat{amt}{tax}: *Inferred Off-Chain Association* with zero traced on-chain volume.")
    if extracted.get("claimed_usd_amounts"):
        lines.append(f"* Platform/chat balance claim(s): {', '.join(extracted['claimed_usd_amounts'])} (compare with on-chain outflows above).")

    lines += ["", "---", "", "## 2. DRAFT EMERGENCY ASSET-FREEZE REQUEST"]
    if not roles["cex"]:
        lines.append("No exchange endpoint was identified, so no exchange-directed freeze request can be drafted yet. "
                     "Extend the trace (more hops) or add evidence, then regenerate.")
        return "\n".join(lines) + "\n"

    for wallet in roles["cex"]:
        rows = traced_df[traced_df["to_wallet"] == wallet]
        name = _short(rows.iloc[0]["to_label"])
        total = rows["amount_eth"].sum()
        lines += [
            "",
            f"### Request to: {name}",
            f"**TO:** {name} Law Enforcement & Compliance Operations Team  ",
            f"**SUBJECT:** URGENT ASSET FREEZE REQUEST - Suspected proceeds of fraud ({total:.2f} ETH)",
            "",
            "Dear Compliance Officer,",
            "",
            "We request an immediate precautionary freeze on customer deposit accounts credited via the following "
            "Ethereum Mainnet transactions linked to an active fraud investigation (verification status shown per transaction):",
            "",
            f"* **Target Exchange Deposit Endpoint:** `{wallet}` ({name})",
            "* **Consolidation Transactions:**",
        ]
        for _, r in rows.iterrows():
            lines.append(f"  - `{r['tx_hash']}` - {r['amount_eth']} ETH at {r['timestamp']} (status: {r['verification']})")
        if roles["deposit"]:
            lines.append("* **Originating Deposit Wallet(s):** " + ", ".join(f"`{w}`" for w in roles["deposit"]))
        if roles["mule"]:
            lines.append("* **Intermediary Wallet(s):** " + ", ".join(f"`{w}`" for w in roles["mule"]))

    lines += [
        "",
        "### Requested Actions:",
        "1. Place an immediate temporary administrative hold on the internal UID account(s) that received the deposits listed above.",
        "2. Preserve KYC records, IP login logs, and withdrawal history associated with the beneficiary UID pending formal legal process.",
        "",
        "**Case reference:** [to be completed]  ",
        "**Requesting officer / agency / contact:** [to be completed]  ",
        "*Draft for investigator review. Not submitted. Confirm all unverified records before sending.*",
    ]
    return "\n".join(lines) + "\n"


def generate_freeze_report(victim_report: str, extracted: dict, traced_df: pd.DataFrame, api_key: str = "") -> str:
    """Produces an evidence-backed investigation summary and draft asset-freeze request."""
    default_report = _build_default_report(victim_report, extracted, traced_df)

    if not api_key.strip():
        return default_report

    try:
        from google import genai
        client = genai.Client(api_key=api_key.strip())
        prompt = (
            "Based on this forensic summary, refine it into a sharp law-enforcement report and asset-freeze warrant. "
            "Keep every wallet address, tx hash, amount, timestamp and verification status exactly as given, and do not "
            "describe unverified items as verified:\n\n" + default_report
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        ai_text = response.text
    except Exception as e:
        return default_report + f"\n> Note: AI refinement unavailable ({type(e).__name__}); showing the evidence-derived draft.\n"

    ok, reason = validate_ai_report(ai_text, default_report)
    if ok:
        return ai_text + "\n\n---\n*AI-refined draft. All wallet addresses and transaction hashes were checked against the source evidence.*\n"
    return default_report + f"\n> Note: the AI refinement was discarded because {reason}. Showing the evidence-derived draft.\n"
# reporter.py
import json
import pandas as pd

def build_interactive_graph_html(traced_df: pd.DataFrame, extracted_wallets: list) -> str:
    """Generates a clean Vis.js graph with individualized edge curve roundness so multi-outgoing labels never overlap."""
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
                    color, level = "#0ea5e9", 0
                elif "CEX" in label or "Binance" in label:
                    color, level = "#10b981", 3
                elif wallet in extracted_wallets:
                    color, level = "#ef4444", 1
                else:
                    color, level = "#059669", 2

                nodes[wallet] = {
                    "id": wallet,
                    "label": f"{label}\n({wallet[:6]}...{wallet[-4:]})",
                    "title": f"Full Address: {wallet}\nRole: {label}",
                    "color": {
                        "background": "#0d1510",
                        "border": color,
                        "highlight": {"background": "#14281a", "border": color}
                    },
                    "level": level,
                    "shape": "box",
                    "margin": 14,
                    "font": {"color": "#f8fafc", "face": "Courier New, monospace", "size": 13}
                }

    edge_idx = 0
    for _, row in traced_df.iterrows():
        edge_idx += 1
        roundness = 0.25 if edge_idx % 2 != 0 else -0.35

        edges.append({
            "from": row["from_wallet"],
            "to": row["to_wallet"],
            "label": f"{row['amount_eth']} ETH  [{row['timestamp'][11:16]}]",
            "title": f"Tx Hash: {row['tx_hash']}\nStage: {row['hop_stage']}",
            "arrows": "to",
            "dashes": False,
            "width": 2,
            "smooth": {"enabled": True, "type": "cubicBezier", "roundness": roundness},
            "color": {"color": "#059669", "highlight": "#10b981"},
            "font": {
                "color": "#94a3b8",
                "size": 11,
                "face": "Courier New, monospace",
                "align": "middle",
                "background": "none",
                "strokeWidth": 0
            }
        })

    extortion_idx = 0
    for w in extracted_wallets:
        if w not in nodes:
            extortion_idx += 1
            nodes[w] = {
                "id": w,
                "label": f"Extortion Tax Wallet {extortion_idx} (Inferred)\n({w[:6]}...{w[-4:]})",
                "title": f"Address: {w}\nStatus: Inferred Off-Chain Association",
                "color": {
                    "background": "#0d1510",
                    "border": "#a855f7",
                    "highlight": {"background": "#14281a", "border": "#a855f7"}
                },
                "level": 1,
                "shape": "box",
                "margin": 14,
                "font": {"color": "#f8fafc", "face": "Courier New, monospace", "size": 13}
            }
            if victim_wallet:
                edges.append({
                    "from": victim_wallet,
                    "to": w,
                    "label": "3.2 ETH Demanded [Inferred]",
                    "title": "Off-Chain Extortion Demand in Chat Log",
                    "arrows": "to",
                    "dashes": [4, 4],
                    "width": 1.5,
                    "smooth": {"enabled": True, "type": "cubicBezier", "roundness": -0.6},
                    "color": {"color": "#c084fc", "highlight": "#e9d5ff"},
                    "font": {
                        "color": "#d8b4fe",
                        "size": 11,
                        "face": "Courier New, monospace",
                        "align": "middle",
                        "background": "none",
                        "strokeWidth": 0
                    }
                })

    nodes_json = json.dumps(list(nodes.values()))
    edges_json = json.dumps(edges)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
      <style>
        body {{ margin: 0; padding: 0; background-color: #090d0a; }}
        #mynetwork {{ width: 100%; height: 460px; background-color: #090d0a; border: 1px solid #14281a; border-radius: 6px; }}
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


def generate_freeze_report(victim_report: str, extracted: dict, traced_df: pd.DataFrame, api_key: str = "") -> str:
    """Dynamically generates an evidence-backed investigation summary and draft asset-freeze request from current case inputs."""
    total_victim_eth = traced_df[traced_df["from_label"].str.contains("Victim")]["amount_eth"].sum() if not traced_df.empty else 0.0
    cex_rows = traced_df[traced_df["to_label"].str.contains("CEX|Binance")] if not traced_df.empty else pd.DataFrame()
    total_cex_eth = cex_rows["amount_eth"].sum() if not cex_rows.empty else 0.0
    cex_wallets = cex_rows["to_wallet"].unique().tolist() if not cex_rows.empty else []
    cex_tx_hashes = cex_rows["tx_hash"].tolist() if not cex_rows.empty else []

    extracted_wallets_str = "\n".join([f"  - `{w}`" for w in extracted.get("extracted_wallets", [])]) or "  - None extracted"
    extracted_txs_str = "\n".join([f"  - `{t}`" for t in extracted.get("extracted_tx_hashes", [])]) or "  - None extracted"

    default_report = f"""# LAW ENFORCEMENT & COMPLIANCE INVESTIGATION REPORT
**Case Summary / Victim Statement:**  
> {victim_report.strip()}

**Total Victim Loss Verified On-Chain:** {total_victim_eth:.2f} ETH  
**Total Funds Traced to Exchange Endpoint:** {total_cex_eth:.2f} ETH  

---

## 1. Evidence Correlation Summary
* **Extracted Off-Chain Entities:**
{extracted_wallets_str}
* **Extracted Transaction Hashes:**
{extracted_txs_str}
* **Verified On-Chain Movement:** Exactly **{total_victim_eth:.2f} ETH** was mapped across blockchain transaction records, consolidating **{total_cex_eth:.2f} ETH** into exchange deposit endpoints (`{cex_wallets[0] if cex_wallets else 'Pending Target Identification'}`).

---

## 2. DRAFT EMERGENCY ASSET-FREEZE REQUEST
**TO:** Centralized Exchange Compliance & Law Enforcement Operations Team  
**SUBJECT:** URGENT ASSET FREEZE REQUEST – Proceeds of Financial Fraud ({total_cex_eth:.2f} ETH)

Dear Compliance Officer,

We request an immediate administrative hold on customer accounts credited via the following verified transaction records:

* **Target Exchange Deposit Endpoint:** `{cex_wallets[0] if cex_wallets else 'N/A'}`
* **Consolidation Transaction Hashes:**
{chr(10).join([f'  - `{h}`' for h in cex_tx_hashes]) if cex_tx_hashes else '  - Refer to attached hop ledger'}

### Requested Actions:
1. Place an immediate temporary hold on the beneficiary UID account(s) corresponding to these deposits.
2. Preserve KYC records, login logs, and transactional history pending formal subpoena issuance.
"""

    if not api_key.strip():
        return default_report

    try:
        from google import genai
        client = genai.Client(api_key=api_key.strip())
        prompt = (
            f"Based on this forensic case data, refine it into a sharp law-enforcement report and asset-freeze warrant. "
            f"Keep all exact wallet addresses and tx hashes intact:\n\n{default_report}"
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text
    except Exception:
        return default_report
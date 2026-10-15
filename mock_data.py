# mock_data.py

SAMPLE_VICTIM_REPORT = """
Victim Name: Rohan Mehta
Incident Type: Pig-Butchering Crypto Investment Scam (ApexQuant VIP)
Summary: Contacted on WhatsApp by 'Elena (ApexQuant Senior Analyst)' claiming 18% weekly returns on automated ETH arbitrage. 
Instructed to transfer funds to a platform deposit wallet. When I attempted to withdraw, they demanded a 25% 'unlock tax' and froze my account.
"""

SAMPLE_CHAT_LOG = """
[2026-10-12 09:14:22] Elena_ApexQuant: Welcome to the ApexQuant institutional arbitrage tier, Rohan!
[2026-10-12 09:16:05] Elena_ApexQuant: Deposit your initial tranche to our smart liquidity node: 0x71C95911E9a5D330f4D621842EC243EE13432921
[2026-10-12 09:42:10] Rohan: Done, transferred 4.5 ETH. Tx hash is 0x8a9f1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcd
[2026-10-12 09:45:00] Elena_ApexQuant: Confirmed! Your dashboard now shows $14,800 with profit boost active.
[2026-10-13 18:10:11] Elena_ApexQuant: Urgent window! Deposit 8.0 ETH before 19:00 to unlock the VIP tier payout to the same wallet 0x71C95911E9a5D330f4D621842EC243EE13432921
[2026-10-13 18:30:45] Rohan: Sent 8.0 ETH! Hash: 0x3f4e5d6c7b8a90123456789abcdef0123456789abcdef0123456789abcdef012
[2026-10-14 11:05:00] Rohan: Why is my withdrawal blocked?
[2026-10-14 11:08:30] Elena_ApexQuant: Compliance hold. Send 3.2 ETH tax to reserve address 0x99B23411E9a5D330f4D621842EC243EE88776655 within 12 hours or funds forfeit.
"""

# Simulated on-chain transaction records (Ethereum Mainnet)
BLOCKCHAIN_LEDGER = [
    {
        "timestamp": "2026-10-12 09:41:55",
        "tx_hash": "0x8a9f1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcd",
        "from_wallet": "0x11A0000000000000000000000000000000009911",
        "from_label": "Victim Wallet (Rohan)",
        "to_wallet": "0x71C95911E9a5D330f4D621842EC243EE13432921",
        "to_label": "Scammer Deposit Node A",
        "amount_eth": 4.5,
        "hop_stage": "Initial Deposit",
        "suspicious_indicator": "Matches wallet shared in off-chain WhatsApp chat",
        "verification": "Verified On-Chain"
    },
    {
        "timestamp": "2026-10-12 09:49:12",
        "tx_hash": "0x22b11c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789ab1111",
        "from_wallet": "0x71C95911E9a5D330f4D621842EC243EE13432921",
        "from_label": "Scammer Deposit Node A",
        "to_wallet": "0x44D88822E9a5D330f4D621842EC243EE55443322",
        "to_label": "Intermediary Mule Wallet 1",
        "amount_eth": 4.48,
        "hop_stage": "Hop 1 (Rapid Dispersion)",
        "suspicious_indicator": "Rapid peel hop (<8 mins after victim deposit) despite platform claiming funds are staked",
        "verification": "Verified On-Chain"
    },
    {
        "timestamp": "2026-10-13 18:30:10",
        "tx_hash": "0x3f4e5d6c7b8a90123456789abcdef0123456789abcdef0123456789abcdef012",
        "from_wallet": "0x11A0000000000000000000000000000000009911",
        "from_label": "Victim Wallet (Rohan)",
        "to_wallet": "0x71C95911E9a5D330f4D621842EC243EE13432921",
        "to_label": "Scammer Deposit Node A",
        "amount_eth": 8.0,
        "hop_stage": "Second Deposit",
        "suspicious_indicator": "High-value transfer following urgent off-chain pressure tactic",
        "verification": "Verified On-Chain"
    },
    {
        "timestamp": "2026-10-13 18:34:02",
        "tx_hash": "0x77c99d3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789ab2222",
        "from_wallet": "0x71C95911E9a5D330f4D621842EC243EE13432921",
        "from_label": "Scammer Deposit Node A",
        "to_wallet": "0x44D88822E9a5D330f4D621842EC243EE55443322",
        "to_label": "Intermediary Mule Wallet 1",
        "amount_eth": 5.0,
        "hop_stage": "Hop 1 (Split Branch A)",
        "suspicious_indicator": "Fund splitting within 4 minutes of receipt to obfuscate trail",
        "verification": "Verified On-Chain"
    },
    {
        "timestamp": "2026-10-13 18:35:19",
        "tx_hash": "0x88d00e3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789ab3333",
        "from_wallet": "0x71C95911E9a5D330f4D621842EC243EE13432921",
        "from_label": "Scammer Deposit Node A",
        "to_wallet": "0x66F11199E9a5D330f4D621842EC243EE99001122",
        "to_label": "Intermediary Mule Wallet 2",
        "amount_eth": 2.98,
        "hop_stage": "Hop 1 (Split Branch B)",
        "suspicious_indicator": "Parallel peel split to secondary transit wallet",
        "verification": "Verified On-Chain"
    },
    {
        "timestamp": "2026-10-14 02:15:40",
        "tx_hash": "0x99e11f3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789ab4444",
        "from_wallet": "0x44D88822E9a5D330f4D621842EC243EE55443322",
        "from_label": "Intermediary Mule Wallet 1",
        "to_wallet": "0x28C6c06298d514Db089934071355E5743bf21d60",
        "to_label": "Binance Hot Wallet 14 (CEX Endpoint)",
        "amount_eth": 9.45,
        "hop_stage": "Hop 2 (Exchange Cash-Out)",
        "suspicious_indicator": "Consolidation into KYC-regulated Centralized Exchange deposit endpoint",
        "verification": "Verified On-Chain"
    },
    {
        "timestamp": "2026-10-14 02:22:10",
        "tx_hash": "0xaae2203d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789ab5555",
        "from_wallet": "0x66F11199E9a5D330f4D621842EC243EE99001122",
        "from_label": "Intermediary Mule Wallet 2",
        "to_wallet": "0x28C6c06298d514Db089934071355E5743bf21d60",
        "to_label": "Binance Hot Wallet 14 (CEX Endpoint)",
        "amount_eth": 2.95,
        "hop_stage": "Hop 2 (Exchange Cash-Out)",
        "suspicious_indicator": "Re-convergence of split funds into same CEX endpoint within 7 minutes",
        "verification": "Verified On-Chain"
    }
]
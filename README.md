# chainsleuth-forensics
ChainSleuth Forensics A Python-based cybersecurity and forensics tool built with Streamlit and Vis.js for investigating cryptocurrency scams (pig-butchering, ransomware, phishing), tracing multi-hop fund movements, and generating automated CEX asset-freeze requests.

PS 01 — Cryptocurrency Scam Investigation and Fund Tracing
Financial crime investigators analyzing pig-butchering scams, ransomware extortion, or phishing operations
struggle to correlate off-chain evidence with on-chain crypto wallet activity. Victims submit fragmented
evidence—including Telegram/WhatsApp chat exports, fake investment platform screenshots, and transaction
hashes. Manually mapping victim timeline statements against blockchain wallet hops to trace fund movements to
centralized exchanges takes days, causing investigators to miss critical windows to request asset freezes. Develop
a solution to this issue by building a platform that helps investigators analyze cryptocurrency scams by combining
victim-submitted evidence with blockchain transaction records.
The platform should:
1. ■ Extract evidence: Accept victim reports, chat exports, transaction hashes and
wallet addresses to identify relevant entities, timestamps and transaction details.
2. ■ Trace transactions: Retrieve or process blockchain records to map fund
movements across wallet addresses and highlight suspicious transaction paths.
3. ■ Correlate evidence: Combine chat evidence and transaction histories into a
chronological incident timeline, linking findings to their supporting evidence.
4. ■ Visualize fund flows: Provide an interactive transaction graph showing
wallet-to-wallet transfers, amounts, timestamps and potential exchange endpoints where verifiable.
5. ■ Generate investigation reports: Produce an evidence-backed case summary and
a draft asset-freeze request that investigators can review and submit through appropriate channels. The solution
should prioritize traceable evidence, explainable findings and clear distinctions between verified transactions and
inferred associations. A prototype may focus on one blockchain and a defined set of evidence formats.

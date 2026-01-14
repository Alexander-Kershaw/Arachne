// Create indexes

CREATE INDEX tx_ts IF NOT EXISTS
FOR (t:Transaction) ON (t.ts);

CREATE INDEX tx_amount IF NOT EXISTS
FOR (t:Transaction) ON (t.amount);

CREATE INDEX merchant_mcc IF NOT EXISTS
FOR (m:Merchant) ON (m.mcc);

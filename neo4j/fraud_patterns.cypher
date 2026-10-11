// ==============================================================================
// FRAUD DETECTION SYSTEM — GRAPH FRAUD PATTERNS (NEO4J 5.26 LTS)
// ==============================================================================
//
// File: neo4j/fraud_patterns.cypher
// Purpose: Cypher pattern queries for graph-based fraud and risk indicator detection.
//
// Graph Model:
//   (:Account)-[:PERFORMED]->(:Transaction)
//   (:Transaction)-[:USED_DEVICE]->(:Device)
//   (:Transaction)-[:ORIGINATED_FROM]->(:IP)
//   (:Transaction)-[:PAID_TO]->(:Merchant)
//   (:Account)-[:ACCESSED_VIA]->(:Device)
//   (:Account)-[:CONNECTED_FROM]->(:IP)
//
// ==============================================================================


// ------------------------------------------------------------------------------
// DESCRIPTIVE STATISTICS (BASELINE FOR HIGH-VALUE THRESHOLDING)
// ------------------------------------------------------------------------------
// Calculate distribution parameters across all ingested transaction nodes:
// Count, Min, Max, Mean, Standard Deviation, Median (p50), 75th percentile (p75).

MATCH (t:Transaction)
RETURN count(t) AS count,
       min(t.transaction_amount) AS min_amount,
       max(t.transaction_amount) AS max_amount,
       avg(t.transaction_amount) AS avg_amount,
       stDev(t.transaction_amount) AS std_amount,
       percentileCont(t.transaction_amount, 0.5) AS median_amount,
       percentileCont(t.transaction_amount, 0.75) AS p75_amount;


// ------------------------------------------------------------------------------
// PATTERN 1: SHARED DEVICE
// ------------------------------------------------------------------------------
// Find devices used by multiple distinct accounts.
// Concept: (Account)-[:ACCESSED_VIA]->(Device)<-[:ACCESSED_VIA]-(OtherAccount)
// Risk Indicator: Multiple accounts operating on a single device can indicate
// credential stuffing, account takeover (ATO), or coordinated fraud rings.

MATCH (a:Account)-[:ACCESSED_VIA]->(d:Device)
WITH d,
     count(DISTINCT a) AS number_of_accounts,
     collect(DISTINCT a.account_id) AS account_ids
WHERE number_of_accounts > 1
RETURN d.device_id AS device_id,
       number_of_accounts,
       account_ids
ORDER BY number_of_accounts DESC;


// ------------------------------------------------------------------------------
// PATTERN 2: SHARED IP ADDRESS
// ------------------------------------------------------------------------------
// Find IP addresses associated with multiple distinct accounts.
// Concept: (Account)-[:CONNECTED_FROM]->(IP)<-[:CONNECTED_FROM]-(OtherAccount)
// Risk Indicator: Proxy/VPN nodes, botnet operations, or shared fraudulent networks.

MATCH (a:Account)-[:CONNECTED_FROM]->(i:IP)
WITH i,
     count(DISTINCT a) AS number_of_accounts,
     collect(DISTINCT a.account_id) AS account_ids
WHERE number_of_accounts > 1
RETURN i.ip_address AS ip_address,
       number_of_accounts,
       account_ids
ORDER BY number_of_accounts DESC;


// ------------------------------------------------------------------------------
// PATTERN 3: MERCHANT CLUSTER
// ------------------------------------------------------------------------------
// Find merchants receiving transactions from multiple accounts.
// Risk Indicator: Rapid clustering on a single merchant can signify collusion,
// mule merchant accounts, or coordinated testing of stolen cards.

MATCH (a:Account)-[:PERFORMED]->(t:Transaction)-[:PAID_TO]->(m:Merchant)
WITH m,
     count(DISTINCT a) AS number_of_accounts,
     count(t) AS transaction_count,
     collect(DISTINCT a.account_id) AS account_ids
WHERE number_of_accounts > 1
RETURN m.merchant_id AS merchant_id,
       number_of_accounts,
       transaction_count,
       account_ids
ORDER BY number_of_accounts DESC, transaction_count DESC;


// ------------------------------------------------------------------------------
// PATTERN 4: HIGH-VALUE TRANSACTIONS
// ------------------------------------------------------------------------------
// Identify transactions significantly exceeding baseline statistical norms.
// Statistical Rule:
//   Observed stats on 10 loaded records:
//     Min: $7.08 | Avg: $190.74 | Median: $116.26 | 75th percentile: $181.23 | Max: $815.96
//   Standard Deviation: $245.65
//   Threshold: transaction_amount > (avg + 1 * stDev) = $436.39
//   (Alternatively: transaction_amount >= p75 = $181.23 for top quartile screening)

MATCH (t:Transaction)
WITH avg(t.transaction_amount) AS baseline_avg,
     stDev(t.transaction_amount) AS baseline_std
MATCH (a:Account)-[:PERFORMED]->(t:Transaction)-[:PAID_TO]->(m:Merchant)
WHERE t.transaction_amount > (baseline_avg + baseline_std)
RETURN t.transaction_id AS transaction_id,
       a.account_id AS account_id,
       t.transaction_amount AS transaction_amount,
       round(baseline_avg, 2) AS baseline_avg,
       round(baseline_avg + baseline_std, 2) AS statistical_threshold,
       t.transaction_date AS transaction_date,
       m.merchant_id AS merchant_id
ORDER BY t.transaction_amount DESC;


// ------------------------------------------------------------------------------
// PATTERN 5: RAPID TRANSACTION VELOCITY
// ------------------------------------------------------------------------------
// Identify accounts with multiple transactions within a short time interval.
// Risk Indicator: High frequency bursts of payments or withdrawals within a tight
// window (e.g. within 3600 seconds / 1 hour, or within 86400 seconds / 24 hours).

MATCH (a:Account)-[:PERFORMED]->(t1:Transaction)
MATCH (a)-[:PERFORMED]->(t2:Transaction)
WHERE t1.transaction_id < t2.transaction_id
  AND t1.transaction_date IS NOT NULL
  AND t2.transaction_date IS NOT NULL
WITH a, t1, t2,
     abs(duration.inSeconds(
         localdatetime(replace(t1.transaction_date, ' ', 'T')),
         localdatetime(replace(t2.transaction_date, ' ', 'T'))
     ).seconds) AS time_difference_seconds
WHERE time_difference_seconds <= 86400
RETURN a.account_id AS account_id,
       t1.transaction_id AS tx1_id,
       t1.transaction_date AS tx1_date,
       t1.transaction_amount AS tx1_amount,
       t2.transaction_id AS tx2_id,
       t2.transaction_date AS tx2_date,
       t2.transaction_amount AS tx2_amount,
       time_difference_seconds
ORDER BY time_difference_seconds ASC;


// ------------------------------------------------------------------------------
// PATTERN 6: MULTI-ENTITY CONNECTION DEGREE
// ------------------------------------------------------------------------------
// Identify accounts connected to multiple devices, IPs, and merchants.
// Risk Indicator: High entity dispersion or rapid device/IP hopping indicates
// potential account compromise or synthetic identities.

MATCH (a:Account)
OPTIONAL MATCH (a)-[:ACCESSED_VIA]->(d:Device)
OPTIONAL MATCH (a)-[:CONNECTED_FROM]->(i:IP)
OPTIONAL MATCH (a)-[:PERFORMED]->(t:Transaction)-[:PAID_TO]->(m:Merchant)
WITH a,
     count(DISTINCT d) AS device_count,
     count(DISTINCT i) AS ip_count,
     count(DISTINCT m) AS merchant_count,
     count(DISTINCT t) AS transaction_count
RETURN a.account_id AS account_id,
       device_count,
       ip_count,
       merchant_count,
       transaction_count,
       (device_count + ip_count + merchant_count) AS total_entity_degree
ORDER BY total_entity_degree DESC, transaction_count DESC;

// ==============================================================================
// FRAUD DETECTION SYSTEM — NEO4J GRAPH SCHEMA & CONSTRAINTS (NEO4J 5.26 LTS)
// ==============================================================================

// ------------------------------------------------------------------------------
// 1. UNIQUENESS CONSTRAINTS
// ------------------------------------------------------------------------------

// Account uniqueness
CREATE CONSTRAINT constraint_account_id IF NOT EXISTS
FOR (a:Account) REQUIRE a.account_id IS UNIQUE;

// Device uniqueness
CREATE CONSTRAINT constraint_device_id IF NOT EXISTS
FOR (d:Device) REQUIRE d.device_id IS UNIQUE;

// IP Address uniqueness
CREATE CONSTRAINT constraint_ip_address IF NOT EXISTS
FOR (i:IP) REQUIRE i.ip_address IS UNIQUE;

// Merchant uniqueness
CREATE CONSTRAINT constraint_merchant_id IF NOT EXISTS
FOR (m:Merchant) REQUIRE m.merchant_id IS UNIQUE;

// Transaction uniqueness
CREATE CONSTRAINT constraint_transaction_id IF NOT EXISTS
FOR (t:Transaction) REQUIRE t.transaction_id IS UNIQUE;

// ------------------------------------------------------------------------------
// 2. PERFORMANCE INDEXES
// ------------------------------------------------------------------------------

// Fast lookup & range queries on transaction date/timestamp
CREATE INDEX index_transaction_date IF NOT EXISTS
FOR (t:Transaction) ON (t.transaction_date);

// Fast filtering on transaction amount (e.g. high-value thresholds)
CREATE INDEX index_transaction_amount IF NOT EXISTS
FOR (t:Transaction) ON (t.transaction_amount);

// ------------------------------------------------------------------------------
// 3. GRAPH MODEL RELATIONSHIPS (FOR INGESTION IN STEP 3)
// ------------------------------------------------------------------------------
//
// (:Account)-[:PERFORMED]->(:Transaction)
// (:Transaction)-[:USED_DEVICE]->(:Device)
// (:Transaction)-[:ORIGINATED_FROM]->(:IP)
// (:Transaction)-[:PAID_TO]->(:Merchant)
// (:Account)-[:ACCESSED_VIA]->(:Device)
// (:Account)-[:CONNECTED_FROM]->(:IP)
//
// ==============================================================================

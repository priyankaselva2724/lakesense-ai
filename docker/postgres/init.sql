-- Warehouse layout and a READ-ONLY role for the AI assistant (database-level guardrail)
create schema if not exists silver;
create schema if not exists gold;
create role llm_readonly login password 'llm_readonly';
grant connect on database lakehouse to llm_readonly;
grant usage on schema gold to llm_readonly;
alter default privileges in schema gold grant select on tables to llm_readonly;
alter role llm_readonly set default_transaction_read_only = on;
alter role llm_readonly set statement_timeout = '15s';

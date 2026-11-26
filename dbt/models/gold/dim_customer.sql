select customer_id, state, email_domain, created_date from {{ source('silver', 'customers') }}

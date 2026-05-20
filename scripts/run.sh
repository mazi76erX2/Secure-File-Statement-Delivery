chmod +x scripts/rebuild-prod.sh

export TF_VAR_statement_api_key="your-real-api-key"
export TF_VAR_db_password="your-real-db-password"
export TF_VAR_redis_password="your-real-redis-password"

scripts/rebuild-prod.sh
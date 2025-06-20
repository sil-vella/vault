#!/bin/bash

# File: /k8s/vault/scripts/check_and_unseal.sh

# Set the log file
LOG_FILE="/k8s/vault/scripts/check_and_unseal.log"
UNSEAL_LOG="/k8s/vault/scripts/unseal.log"

# Set Vault address to use local address
export VAULT_ADDR="http://localhost:8200"

echo "=== $(date) ===" >> "$LOG_FILE"
echo "Checking Vault at $VAULT_ADDR" >> "$LOG_FILE"

# Check Vault health
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${VAULT_ADDR}/v1/sys/health")
echo "Vault health status: $STATUS" >> "$LOG_FILE"

# If sealed or not initialized
if [[ "$STATUS" == "501" || "$STATUS" == "503" ]]; then
  echo "Vault is sealed or unavailable. Attempting unseal..." >> "$LOG_FILE"
  if /k8s/vault/scripts/unseal.sh >> "$UNSEAL_LOG" 2>&1; then
    echo "Unseal script executed successfully." >> "$LOG_FILE"
  else
    echo "Unseal script failed. Check $UNSEAL_LOG for details." >> "$LOG_FILE"
  fi
else
  echo "Vault is healthy ($STATUS). No action needed." >> "$LOG_FILE"
fi 
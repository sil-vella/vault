#!/bin/bash

LOG_FILE="$(dirname "$0")/unseal.log"

# Set Vault address to use local address
export VAULT_ADDR="http://localhost:8200"

echo "===== $(date) Starting unseal process =====" >> "$LOG_FILE" 2>&1

for i in 1 2 3; do
  echo "Retrieving unseal key $i..." >> "$LOG_FILE" 2>&1
  KEY=$(gcloud secrets versions access latest --secret="vault-unseal-key-$i" 2>>"$LOG_FILE")
  if [ $? -ne 0 ]; then
    echo "Failed to retrieve unseal key $i from GCP Secrets" >> "$LOG_FILE"
    continue
  fi

  echo "Unsealing with key $i..." >> "$LOG_FILE"
  vault operator unseal "$KEY" >> "$LOG_FILE" 2>&1
  if [ $? -ne 0 ]; then
    echo "Unseal command with key $i failed" >> "$LOG_FILE"
  else
    echo "Unseal command with key $i succeeded" >> "$LOG_FILE"
  fi
done

echo "===== $(date) Unseal process complete =====" >> "$LOG_FILE" 2>&1 
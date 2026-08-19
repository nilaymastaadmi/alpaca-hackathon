#!/bin/bash
cd ~/alpaca-hackathon
echo '--git status (should NOT list .env)--'
git status --porcelain
echo '--live account check--'
set -a
source .env
set +a
curl -s https://paper-api.alpaca.markets/v2/account \
  -H "APCA-API-KEY-ID: $ALPACA_API_KEY" \
  -H "APCA-API-SECRET-KEY: $ALPACA_SECRET_KEY"
echo

#!/usr/bin/env bash
# DataHub + Marquez bring-up for the AbbVie DataOps PoC.
# Run on the user-provided EC2 instance i-0165db8e63bcdb1d3 (Ubuntu).
set -euo pipefail

echo "==> updating apt"
apt-get update -y
apt-get install -y --no-install-recommends ca-certificates curl gnupg jq awscli

if ! command -v docker >/dev/null 2>&1; then
  echo "==> installing Docker engine"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  source /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME:-$VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable --now docker
fi

DEST=/opt/abbvie/datahub
mkdir -p "$DEST"
cp "$(dirname "$0")/docker-compose.yml" "$DEST/docker-compose.yml"

echo "==> starting DataHub + Marquez stack (this is heavy; first pull ~5 min)"
cd "$DEST"
docker compose pull
docker compose up -d

echo
echo "==> services should be reachable shortly:"
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4 || echo localhost)
echo "    DataHub UI    : http://${PRIVATE_IP}:8080"
echo "    DataHub GMS   : http://${PRIVATE_IP}:8000"
echo "    Marquez API   : http://${PRIVATE_IP}:5000"
echo "    Marquez UI    : http://${PRIVATE_IP}:3000"
echo
echo "==> updating Secrets Manager with the resolved private IP"
SECRET_ID="abbvie-dataops-poc/datahub/endpoints"
REGION="${AWS_REGION:-us-west-2}"
PAYLOAD=$(jq -n \
  --arg gms   "http://${PRIVATE_IP}:8000" \
  --arg front "http://${PRIVATE_IP}:8080" \
  --arg ol    "http://${PRIVATE_IP}:5000" \
  '{datahub_gms_url:$gms,datahub_frontend_url:$front,openlineage_url:$ol,datahub_token:""}')
aws --region "$REGION" secretsmanager put-secret-value \
  --secret-id "$SECRET_ID" --secret-string "$PAYLOAD" || \
  echo "(skipped: instance role may not have secretsmanager:PutSecretValue)"

echo "==> done"

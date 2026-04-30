# DataHub + Marquez on EC2 `i-0165db8e63bcdb1d3`

Brings up the complete catalog + lineage backend used by the DataOps SDK.

## Prereqs

- The Terraform AWS module has been applied (opens ports 8080 / 8000 / 5000 on the EC2 SG and writes endpoint placeholders to Secrets Manager).
- The EC2 has an instance profile with `secretsmanager:PutSecretValue` on `abbvie-dataops-poc/datahub/endpoints` (optional but lets `bootstrap.sh` self-register).

## Bring-up

```bash
ssh ubuntu@<datahub-ec2-public-ip>
sudo mkdir -p /opt/abbvie/datahub
sudo curl -o /opt/abbvie/datahub/docker-compose.yml \
  https://raw.githubusercontent.com/sfc-gh-palapaty/abbvie-dataops-poc-aws/main/apps/datahub/docker-compose.yml
sudo curl -o /opt/abbvie/datahub/bootstrap.sh \
  https://raw.githubusercontent.com/sfc-gh-palapaty/abbvie-dataops-poc-aws/main/apps/datahub/bootstrap.sh
sudo bash /opt/abbvie/datahub/bootstrap.sh
```

After ~5 min you'll have:

| Service | Port | Purpose |
|---|---|---|
| DataHub UI | 8080 | Browse datasets, owners, tags, lineage |
| DataHub GMS REST | 8000 | Used by `DataHubEmitter` in the SDK |
| Marquez API | 5000 | OpenLineage HTTP receiver |
| Marquez UI | 3000 | Run timeline / OL event browser |

## Ingest Marquez lineage into DataHub

The DataHub `openlineage` source pulls Marquez runs into DataHub:

```bash
pip install acryl-datahub[openlineage]
DATAHUB_GMS_URL=http://localhost:8000 \
OPENLINEAGE_URL=http://localhost:5000 \
  datahub ingest -c apps/datahub/datahub-marquez-source.yaml
```

Schedule this hourly via cron (or Airflow) to keep the DataHub lineage UI fresh.

## Smoke test the SDK can reach DataHub

```bash
DATAHUB_GMS_URL=http://<ec2-private-ip>:8000 \
OPENLINEAGE_URL=http://<ec2-private-ip>:5000 \
  abbvie-dataops run --manifest manifests/suitecrm-crm.yaml --profile promote
```

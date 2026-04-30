# DataHub + Marquez bring-up (EC2 `i-0165db8e63bcdb1d3`)

The Terraform AWS module already opens ingress on ports `8080` (DataHub frontend), `8000` (DataHub GMS), and `5000` (Marquez) on the EC2's existing security group.

This folder is intentionally **empty of resources** — the EC2 is user-managed. Use the bootstrap script under `apps/datahub/` from inside the instance:

```bash
ssh ubuntu@<datahub-ec2-public-ip>
sudo bash /opt/abbvie/datahub/bootstrap.sh
```

After bring-up, update the `abbvie-dataops-poc/datahub/endpoints` secret in AWS Secrets Manager with the actual reachable URL (private IP if SDK runs from EMR/ECS, public IP if running from your laptop).

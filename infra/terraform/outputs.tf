# Pipe into the in-cluster Secret without the token ever touching git:
#   kubectl create secret generic cloudflared-token \
#     --from-literal=token="$(terraform -chdir=infra/terraform output -raw cloudflared_token)"
output "cloudflared_token" {
  description = "Run token for the in-cluster cloudflared Deployment."
  value       = data.cloudflare_zero_trust_tunnel_cloudflared_token.app.token
  sensitive   = true
}

output "tunnel_id" {
  description = "Cloudflare Tunnel ID."
  value       = cloudflare_zero_trust_tunnel_cloudflared.app.id
}

# Public apex the app is served on (derived from the Cloudflare zone, see
# local.app_hostname in cloudflare.tf). prod-stack.sh reads this to point the
# Tigris upload-notification webhook at https://<host>/api/upload-processing-jobs.
output "app_hostname" {
  description = "Public hostname the app is served on (e.g. hexagone.one)."
  value       = local.app_hostname
}

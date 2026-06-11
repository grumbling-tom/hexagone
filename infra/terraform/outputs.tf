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

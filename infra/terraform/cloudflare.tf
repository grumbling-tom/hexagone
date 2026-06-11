# Cloudflare edge — the app's public entry point. Replaces the manual dashboard
# steps in infra/k8s/README.md. The in-cluster cloudflared Deployment connects
# this tunnel OUTBOUND; nothing inbound is opened on the Mac mini.
#
# NOTE: cloudflare provider v5 renamed these from v4 (cloudflare_tunnel*,
# cloudflare_record) and moved several blocks to nested attributes. Verify exact
# schema before apply:
# https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs

# The zone_id is the single source of truth for the domain — derive the public
# hostname from it rather than repeating the domain in a variable. No subdomain
# for now, so the app is served at the apex.
data "cloudflare_zone" "app" {
  zone_id = var.cloudflare_zone_id
}

locals {
  app_hostname = data.cloudflare_zone.app.name
}

resource "cloudflare_zero_trust_tunnel_cloudflared" "app" {
  account_id = var.cloudflare_account_id
  name       = "hexagone-mini"
  config_src = "cloudflare" # routing managed here via API, not a local config file
}

resource "cloudflare_zero_trust_tunnel_cloudflared_config" "app" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.app.id

  config = {
    ingress = [
      {
        hostname = local.app_hostname
        # In-cluster Traefik applies the Ingress rules in infra/k8s.
        service = "http://traefik.kube-system.svc.cluster.local:80"
      },
      # Required catch-all.
      { service = "http_status:404" },
    ]
  }
}

# Proxied CNAME -> the tunnel. Cloudflare manages TLS for this hostname.
resource "cloudflare_dns_record" "app" {
  zone_id = var.cloudflare_zone_id
  name    = local.app_hostname
  type    = "CNAME"
  content = "${cloudflare_zero_trust_tunnel_cloudflared.app.id}.cfargotunnel.com"
  proxied = true
  ttl     = 1
}

# The run token the in-cluster cloudflared Deployment authenticates with.
data "cloudflare_zero_trust_tunnel_cloudflared_token" "app" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.app.id
}

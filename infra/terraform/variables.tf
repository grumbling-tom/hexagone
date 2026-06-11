variable "cloudflare_api_token" {
  description = "Cloudflare API token — Account: Cloudflare Tunnel edit; Zone: DNS edit."
  type        = string
  sensitive   = true
}

variable "cloudflare_account_id" {
  description = "Cloudflare account ID that owns the tunnel."
  type        = string
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID for the app's domain. The public hostname is derived from this (see local.app_hostname in cloudflare.tf)."
  type        = string
}

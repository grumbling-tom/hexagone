# Non-secret inputs — safe to commit. These are identifiers, not credentials:
# they only name which account/zone a request targets and grant no access on
# their own. The sensitive values stay out of source:
#   - cloudflare_api_token  -> macOS Keychain (see README "Cloudflare API token")
#   - cloudflared run token -> terraform output, piped straight into a k8s Secret
cloudflare_account_id = "2882cad0207e5536842b1ec75a19adad"
cloudflare_zone_id    = "f0096fd3df9691033f2f540bb5d505c4"

# No app_hostname here by design — it's derived from the zone (served at the
# apex). See local.app_hostname in cloudflare.tf.

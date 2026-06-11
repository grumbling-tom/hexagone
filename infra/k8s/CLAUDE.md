# Infra (k8s) Conventions

## Namespacing — controllers live apart from apps

**App workloads go in `default`.** The backend, web, cloudflared, and the
CloudNativePG `Cluster` CR (the database itself) all live in `default` via the
production overlay's `namespace: default`.

**Controllers and operators live in their own namespace — never `default`.**
Cluster infrastructure (the CloudNativePG operator in `cnpg-system`, an ingress
controller in `kube-system`, future things like cert-manager) is not an app and
stays out of `default`. Reasons:

- **Blast radius** — a stray `kubectl delete ... -n default` can't take out a
  controller that workloads depend on.
- **Scoped RBAC and clean inventory** — `kubectl get all` in `default` shows only
  *your* app; controller RBAC stays confined.
- **Namespace-as-uninstall** — removing a controller is `kubectl delete ns <x>`.

This split is per *component*, not per *resource type*: the CNPG **operator** runs
in `cnpg-system`, but the Postgres **database** it manages (the `Cluster` CR) still
lives in `default` alongside the app. Operators watch across namespaces, so the
controller and the workload it manages don't need to share one.

### Consequence: don't pull operator manifests into the app overlay

The overlay's `namespace: default` transformer rewrites **every resource it
manages** to `default`. An operator's release manifest hardcodes its own
namespace in places Kustomize won't cleanly rewrite — webhook
`clientConfig.service.namespace`, RBAC subjects, cert SANs — so forcing it into
`default` breaks it.

Install operators **out of band** and keep only their app-level CRs in the overlay:

```bash
# operator: one-time, cluster-wide, NOT in the overlay
kubectl apply --server-side -f https://.../cnpg-1.29.0.yaml
```

```yaml
# overlay: only the app-level CR (lands in default, managed by the operator)
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: hexagone-db
```

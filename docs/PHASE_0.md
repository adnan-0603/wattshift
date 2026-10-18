# Phase 0 — local setup and verification

## Prerequisites

Use a computer running Docker Linux containers. Install Python 3.10+, Make, Git, kind and kubectl if missing. Official references:

- https://kind.sigs.k8s.io/docs/user/quick-start/
- https://kind.sigs.k8s.io/docs/user/configuration/
- https://github.com/kubernetes-sigs/kind/releases/tag/v0.31.0
- https://kubernetes.io/docs/tasks/tools/
- https://docs.docker.com/get-started/get-docker/

The reference pair is kind v0.31.0 and Kubernetes v1.35.0, with the official multi-architecture node digest pinned in cluster.yaml. This supports amd64 and arm64; do not install the wrong platform binary. Keep kubectl compatible with Kubernetes 1.35. A newer kind may work, but must pass the runtime checks. Use current vendor installation instructions rather than an unverified download script. Start Docker Desktop/the daemon before continuing.

This setup has one control-plane node to keep resource needs modest. Later LightGBM/Grafana/Kueue work will require a fresh resource check. Ports 8080/8443 must be free; an ingress controller will be added later. This does not enable Docker Desktop's separate built-in Kubernetes cluster.

## Run

From the extracted project directory:

```bash
make test
make review
make doctor
make up
make verify
make status
```

Expected gate evidence: one Ready node, CoreDNS deployment rollout successful, Active `wattshift` namespace and `.local/phase0-verification.json`. That JSON contains no credentials. Share its contents and `make status` output for review. Do not share `.local/kubeconfig`.

For manual inspection use the isolated config, never an accidental current cluster:

```bash
kubectl --kubeconfig .local/kubeconfig --context kind-wattshift get nodes
kubectl --kubeconfig .local/kubeconfig --context kind-wattshift get pods -A
```

`make up` reuses an existing named cluster, checks its node names and Kubernetes version, and fails clearly if incompatible. It does not auto-delete an existing cluster. `make down` explicitly destroys only the named wattshift cluster and its stored data. Use it only if you want that deletion.

## Repository/release gate

The package contains a local Git history bundle. Restore it into an empty directory with `git clone /absolute/path/wattshift-history.bundle wattshift-repo`; the legacy ZIP is supplied outside history and can be copied into `legacy/` if needed. The source review reports whether that optional archive is present.

No remote has been chosen or written. Confirm the intended GitHub owner/repository before attaching origin. Once source review AND actual runtime verification pass, record evidence and create the v0.1 tag/release on that repository. Do not tag now to make the history look complete.

## Next phase

After Phase 0 passes, Phase 1 retrieves and validates real market/generation data and produces the first plots. The previous simulator remains a prototype until its assumptions are reconciled with the Phase 5 evaluation protocol.

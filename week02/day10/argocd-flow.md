# Day 10 — ArgoCD / GitOps mental model

## End-to-end flow (ví dụ thật: cashback-service-id trên stag)

```
App repo ──► CI (Jenkins) ──► Registry ──► GitOps repo ──► ArgoCD ──► K8s controller ──► Pod
```

| Bước | Ai làm | Artifact / output thật |
|---|---|---|
| 1. App repo | dev | commit `363c9d4` trên `feature/CAS-372/tenant-site-paste-link` (cashback-service) |
| 2. CI build/test | Jenkins `BUILD_CASHBACK_SERVICE` | build #21, `mvnw verify` + `docker build` |
| 3. Registry | Jenkins push | `docker.asean-accesstrade.net/accesstrade/cashback-service-id:stag-id-363c9d4-21` |
| 4. GitOps repo | job `DP_ArgoCD_Deployment_Update` (CI Bot) | commit `e86272f2` trong `devops-deployments`: `releases.yaml` `stag-id-21e7316-20 → stag-id-363c9d4-21` |
| 5. ArgoCD | job `DP_ArgoCD_Deployment_Sync` gọi sync | Application `stag-cashback-service-id` render chart `generic` → apply |
| 6. K8s controller | Deployment controller | Deployment đổi image → ReplicaSet mới → Pod mới |

- ArgoCD **không build source**. Nó chỉ đọc Git, render manifest, so với cluster rồi apply (CD + reconciliation).
- Tag `<env>-<cc>-<sha>-<build>` nối được Pod đang chạy ngược về commit app và build Jenkins.

## Flow ArgoCD reconcile

```
Git (desired) ──► ArgoCD: render ──► so sánh với cluster ──► Synced / OutOfSync
                                          │
                                          └─ sync ──► API object (Deployment) ──► controller ──► ReplicaSet ──► Pod
```

Hai vòng reconcile:

| Vòng | So sánh | Ai sửa |
|---|---|---|
| GitOps | Git ↔ object trong cluster | ArgoCD (sync, selfHeal) |
| Kubernetes | `spec` ↔ Pod thật | Deployment / ReplicaSet controller |

## Lab: ArgoCD thật trên minikube `day08`

Application `argocd/app-dev.yaml` trỏ vào repo này: `week02/day09/charts/app` + values/releases của `dev`, namespace `argo-dev`.

| Bước | Kết quả |
|---|---|
| Tạo Application | `OutOfSync / Missing`, revision `a117dd8` = `main` trên GitHub; 3 object chưa có |
| Sync lần 1 (tay, thiếu `syncOptions`) | `Failed: namespaces "argo-dev" not found` |
| Sync lại có `CreateNamespace=true` | `Synced / Healthy`; Pod log `GREETING = hello from dev`, `APP_VERSION = 1.1.0` |
| Owner chain | `Pod ← ReplicaSet/app-6df6686594 ← Deployment/app`; Deployment có tracking-id `argo-dev-app:apps/Deployment:argo-dev/app` |
| Scale tay lên 3 (chưa selfHeal) | `OutOfSync`, chỉ ra `Deployment/app` bị lệch, ArgoCD không tự sửa |
| Bật `automated` + `selfHeal` | về 1 replica, `Synced` |
| Scale tay lên 5 | ArgoCD đè lại về 1 sau ~2s |

## Issue

Sync tay lần đầu fail: `namespaces "argo-dev" not found`.
Root cause: `CreateNamespace=true` nằm trong `spec.syncPolicy`, nhưng lệnh sync tay (patch `operation`) không gửi kèm `syncOptions`, nên ArgoCD không tạo namespace. Gửi lại sync có `syncOptions: [CreateNamespace=true]` thì được (nút Sync trên UI tự gửi kèm).

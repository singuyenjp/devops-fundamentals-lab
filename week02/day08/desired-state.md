# Day 8 — Desired state & manifest

Cluster: minikube profile `day08`. App: `day06-app` (2 version `1.0.0`, `1.1.0`).
Manifest: `deployment.yaml` (= desired state trong Git).

## Object model

| Field | Ai ghi | Ví dụ |
|---|---|---|
| `apiVersion`, `kind` | Sĩ | `apps/v1`, `Deployment` |
| `metadata` | Sĩ + cluster | mình: `name`, `labels`; cluster thêm `uid`, `resourceVersion`, `generation` |
| `spec` | Sĩ | `replicas`, `image`, `env` — **desired state** |
| `status` | cluster | `readyReplicas`, `conditions` — **actual state** |

File trong Git chỉ có `apiVersion, kind, metadata, spec`. `kubectl get -o yaml` có thêm `status`.

## Đổi desired state trong Git

```diff
-  replicas: 1
+  replicas: 2
-          image: day06-app:1.0.0
+          image: day06-app:1.1.0
```

```powershell
kubectl diff -f deployment.yaml     # xem cluster sẽ đổi gì
kubectl apply -f deployment.yaml
kubectl rollout status deploy/day08-app
kubectl get deploy,rs,pod -l app=day08-app
kubectl describe deploy day08-app   # Events
```

Kết quả: ReplicaSet mới `1.1.0` scale 0 → 2, ReplicaSet cũ 1 → 0. `generation=4`, `observedGeneration=4`, `readyReplicas=2`. Log Pod: `APP_VERSION = 1.1.0`.

## Reconciliation

| Thử | Kết quả |
|---|---|
| Xoá Pod | Deployment tạo Pod mới ngay (giữ đúng `replicas`) |
| `kubectl scale --replicas=3` (sửa tay) | cluster chạy 3, Git vẫn 1 → `kubectl diff` báo lệch `3 → 1` |
| `kubectl apply` lại file | về đúng 1 replica |

Sửa tay trên cluster tạo drift. ArgoCD (selfHeal) sẽ tự đưa về Git; ở lab này mình apply lại bằng tay.

## Helm render (repo công ty)

`cashback-service-id` trên stag, render giống ArgoCD:

```powershell
helm template stag charts/infra -f config/environments/stag/values.yaml -f config/environments/stag/releases.yaml
helm template stag-cashback-service-id charts/generic -n stag -f config/app/cashback-service-id.yaml -f <values từ Application>
```

Ra 5 object: Deployment, Service, ConfigMap, ExternalSecret, IngressRoute. Deployment có `replicas: 1`, image `...cashback-service-id:stag-id-32aafb8-15`, không có `status`.

## Issue

Pod cũ bị giữ ~30s khi rollout.
Root cause: app chạy là PID 1 và không xử lý SIGTERM, nên phải chờ hết `terminationGracePeriodSeconds` (30s) mới bị kill. Kiểm chứng: `docker stop -t 10` mất đúng 10s, exit code 137.

# Day 17 — Troubleshooting GitOps sync

ArgoCD ở day 10 chạy trên minikube local nên không dùng lại được trong CI. Lab này **mô phỏng bước sync** bằng đúng các bước ArgoCD làm: render chart → apply → chờ healthy, trên cluster `kind` tạm trong GitHub Actions (`.github/workflows/day17-sync.yml`, branch `feature/day17-gitops-sync`).

```
Git (values / releases / sync.env) ──► helm template ──► kubectl apply ──► rollout status ──► (fail) describe + events
        render error                      SyncFailed                          Degraded
```

Config nằm trong Git: `week03/day17/config/dev/{values.yaml, releases.yaml, sync.env}`, dùng chart `week02/day09/charts/app`. `sync.env` đóng vai `syncOptions` + quyền của người sync (`CREATE_NAMESPACE`, `SYNC_AS`).

## Phân loại lỗi sync

| Lớp | Xảy ra ở bước | Trong ArgoCD sẽ thấy |
|---|---|---|
| Render / value | `helm template` hoặc apply từ output | `ComparisonError` / `SyncFailed` kèm message từ API |
| Config / manifest | `kubectl apply` bị API từ chối | `SyncFailed`, resource lỗi ghi rõ trong sync result |
| RBAC | `kubectl apply` | `SyncFailed` ... `forbidden` |
| Resource / runtime | apply xong, rollout không xong | `Synced` nhưng `Progressing` → `Degraded` |

Trace luôn đi 2 tầng: message ở ArgoCD → resource nào lỗi → `get/describe` status + Events của resource đó → sửa trong Git.

## Baseline

Commit `ec09413`, run `38394559282` xanh: render `replicas: 1`, image `nginxinc/nginx-unprivileged:1.27-alpine`; `configmap/app`, `service/app`, `deployment.apps/app` created; `deployment "app" successfully rolled out`.

Drift demo trong cùng run: scale tay lên 3 rồi `kubectl diff -f rendered.yaml` ra `- replicas: 3` / `+ replicas: 1` — chính là diff mà ArgoCD hiển thị khi `OutOfSync`.

## 4 case

| # | Commit lỗi | Run | Step fail | Message | Lớp |
|---|---|---|---|---|---|
| A | `d6f6152` `replicaCount: "two"` | `38394735456` | Sync (apply) | `Deployment in version "v1" cannot be handled as a Deployment: json: cannot unmarshal string into Go struct field DeploymentSpec.spec.replicas of type int32` | value |
| B | `523ec7f` `CREATE_NAMESPACE=false` | `38394916336` | Sync (apply) | `namespaces "sync-dev" not found` (3 resource đều lỗi) | config |
| C | `750af60` `SYNC_AS=viewer` | `38395060755` | Sync (apply) | `deployments.apps is forbidden: User "system:serviceaccount:default:viewer" cannot create resource ... in the namespace "sync-dev"` | RBAC |
| D | `cad3936` tag `9.9.9` | `38395236545` | Health (rollout status) | `timed out waiting for the condition` | runtime |

Revert tương ứng: A `8e9fe94`, B `71cc8d6`, C `344d8ea`, D `d2900e6` — sau mỗi revert run xanh lại (run D: `38395508506`).

### Case A — value sai kiểu
- Trace: step Sync fail → message chỉ đúng field `spec.replicas` kiểu `int32`, resource `Deployment`.
- Quan sát: `configmap/app` và `service/app` đã `created`, chỉ `Deployment` bị từ chối → sync lỗi một phần, Git và cluster lệch nhau (ArgoCD sẽ hiện từng resource Synced / Failed riêng).
- Root cause: `values.yaml` truyền chuỗi `"two"` vào chỗ cần số; `helm template` vẫn render ra, API server mới từ chối.
- Fix: revert commit về `replicaCount: 1`.

### Case B — namespace chưa có
- Trace: cả 3 resource cùng một lỗi `namespaces "sync-dev" not found` → lỗi chung, không phải riêng resource nào.
- Root cause: không ai tạo namespace; giống issue day 10 (sync tay thiếu `CreateNamespace=true`).
- Fix: bật lại `CREATE_NAMESPACE=true` (trong ArgoCD là `syncOptions: CreateNamespace=true`).

### Case C — không đủ quyền
- Trace: message `forbidden` nói rõ ai (`serviceaccount:default:viewer`), làm gì (`create`), resource nào, namespace nào.
- Root cause: identity chỉ có quyền `view`, không có quyền tạo.
- Fix: sync bằng identity đúng quyền (`admin` ở lab). Không nới quyền bừa để cho qua lỗi.

### Case D — sync xong nhưng không healthy
- Step Sync **xanh** (`created`), step Health fail sau 60s. Nếu chỉ nhìn bước apply thì tưởng ổn: tương ứng `Synced` nhưng `Degraded`.
- Xuống resource: `deployment 0/1` → `replicaset` 1 desired / 0 ready → `pod app-... 0/1 ErrImagePull`.
- Events của Pod: `Scheduled` (đã có node) → `Failed to pull image "nginxinc/nginx-unprivileged:9.9.9": ... NotFound` → `ErrImagePull` → `Back-off pulling image` → `ImagePullBackOff`.
- Root cause: tag `9.9.9` không tồn tại trong registry. Pod đã được lịch lên node nên không phải lỗi `Pending`.
- Fix: revert về tag `1.27-alpine`.

## Issue

Chưa gặp lỗi ngoài các case cố ý. Chọn mô phỏng thay vì ArgoCD thật vì lab ArgoCD ở day 10 nằm trên minikube local; message lỗi ở các case A–C là message của API server, ArgoCD chỉ hiển thị lại.

## Bài học

- `SyncFailed` chỉ là bước đầu: phải đọc message, tìm resource lỗi rồi xuống status/events.
- Phân biệt: lỗi ở render/apply (Git sai) · quyền (RBAC) · apply được nhưng chạy không nổi (Degraded).
- Sync xanh chưa chắc healthy; vì vậy luôn có bước kiểm tra health sau sync.
- Mọi fix đều là commit trong Git (revert), không `kubectl edit` trên cluster.

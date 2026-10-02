# Day 9 — Environment, image update qua GitOps, Pod config

Làm theo cấu trúc repo `devops-deployments`, thu nhỏ lại:

```
week02/day09/
├── charts/app/                    # chart dùng chung (≈ charts/generic)
└── config/environments/
    ├── dev/  values.yaml          # replicas, env của dev
    │         releases.yaml        # chỉ chứa image tag (CI sửa file này)
    └── stag/ values.yaml
              releases.yaml
```

Sync (lab dùng helm, công ty là ArgoCD):

```powershell
helm upgrade --install app charts/app -n dev --create-namespace `
  -f config/environments/dev/values.yaml -f config/environments/dev/releases.yaml
```

## Tách env

| | dev | stag |
|---|---|---|
| namespace | `dev` | `stag` |
| replicas | 1 | 2 |
| GREETING | `hello from dev` | `hello from stag` |
| image tag | `1.1.0` (sau PR) | `1.0.0` |

Render 2 env chỉ khác đúng những gì khai trong `values.yaml` / `releases.yaml`.

## Update image cho dev qua PR

```diff
 # config/environments/dev/releases.yaml
 image:
-  tag: "1.0.0"
+  tag: "1.1.0"
```

Sau khi sync: dev chạy `day06-app:1.1.0`, stag vẫn `1.0.0` → đổi 1 env không đụng env khác.

## Pod config

| Thành phần | Trong chart | Ảnh hưởng |
|---|---|---|
| ConfigMap | `env` → `envFrom.configMapRef` | env của app, chỉ đọc **lúc Pod start** |
| Secret | `envFrom.secretRef` (optional, không để trong Git) | giống ConfigMap nhưng cho giá trị nhạy cảm |
| startupProbe | `GET /` mỗi 2s, tối đa 10 lần | chưa pass thì chưa chạy readiness/liveness |
| readinessProbe | `GET /` mỗi 5s | fail → Pod `0/1`, bị rút khỏi Service |
| livenessProbe | `GET /` mỗi 10s | fail → restart container |

### Thử readiness sai port (9999)

- Pod `Running` nhưng `0/1`.
- EndpointSlice: `ready=false` → Service không gửi traffic.
- Event: `Readiness probe failed: ... :9999: connect: connection refused`.

### Đổi ConfigMap

- `kubectl patch` ConfigMap → Pod đang chạy **vẫn giữ giá trị cũ** (env chỉ đọc lúc start).
- Đổi qua values rồi sync → annotation `checksum/config` đổi → Deployment rollout ReplicaSet mới → Pod mới có env mới.

## Issue

Sau khi `kubectl patch` ConfigMap, `helm upgrade` từ Git bị fail: `conflict with "kubectl-patch" ... .data.GREETING`.
Root cause: Helm 4 dùng server-side apply; sửa tay làm `kubectl-patch` thành chủ của field đó, nên lần sync sau từ Git bị chặn. Sync lại với `--force-conflicts` để Git lấy lại field. → Sửa tay trên cluster không chỉ tạo drift mà còn làm hỏng lần deploy sau.

## Ở repo công ty

- Mỗi env một thư mục `config/environments/<env>/` có `values.yaml` + `releases.yaml`; vd `bff-common-id`: dev 1 replica tag `0.0.1-47abf0e-SNAPSHOT`, stag 0 replica tag `0.0.1-6b54f26-SNAPSHOT`.
- Chart `generic` có hỗ trợ startup/liveness/readiness probe, nhưng các app đang để comment (vd `config/app/bff-common-id.yaml`); moneycore và cashback-service không khai probe.
- ConfigMap từ `env`/`data`, Secret từ `external_secret` (AWS), cả hai vào Pod qua `envFrom`.

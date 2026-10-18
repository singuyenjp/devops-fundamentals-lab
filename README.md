# devops-fundamentals-lab

Repo học DevOps Fundamentals (20 ngày): Git, Docker, registry, GitOps với Helm/ArgoCD, release, rollback và troubleshooting. Mỗi ngày một thư mục trong `week01`–`week03`, mỗi thay đổi đi qua một PR.

Bảng ngày ↔ PR ↔ commit ↔ pipeline run nằm ở [EVIDENCE.md](EVIDENCE.md).

## Cấu trúc

| Thư mục | Nội dung |
|---|---|
| `week01/` | Git (branch, conflict, rebase), PR, revert, traceability |
| `week02/day06` | App Python, Dockerfile, tag image |
| `week02/day07` | Registry local, phân biệt lỗi build/auth/push/pull |
| `week02/day08` | Deployment, desired state vs actual state |
| `week02/day09` | Chart Helm dùng chung (`charts/app`) + `config/environments/{dev,stag}` |
| `week02/day10` | ArgoCD Application (`argocd/app-dev.yaml`) |
| `week03/day14` | Verify release, bad release, rollback (`verify-release.py`) |
| `week03/day15` | Checklist pre-deploy, `scope-check.sh`, dry-run review |
| `week03/day16`–`18` | Lab troubleshooting: CI, GitOps sync, runtime |
| `.github/workflows/` | Pipeline của lab (chỉ chạy trên branch `feature/dayNN-*`, không chạy trên `main`) |

## Flow

```
code commit ──► PR ──► CI (build, test) ──► image + tag ──► đổi tag trong releases.yaml (PR) ──► ArgoCD sync ──► verify
```

- CI chỉ build và ra image; việc đưa lên cluster là của GitOps (ArgoCD đọc Git rồi apply).
- Desired state nằm trong Git. Không `kubectl edit/patch/scale` trên resource do ArgoCD quản lý.
- Tag image nên có commit SHA (ví dụ `sha-c4ab653`), không dùng `latest`, để lần ngược từ Pod về commit.

## Deploy

Mỗi env có `values.yaml` (replicas, env) và `releases.yaml` (chỉ chứa image tag, phần CI sửa).

```bash
helm upgrade --install app week02/day09/charts/app -n dev --create-namespace \
  -f week02/day09/config/environments/dev/values.yaml \
  -f week02/day09/config/environments/dev/releases.yaml
```

Với ArgoCD: `kubectl apply -f week02/day10/argocd/app-dev.yaml` (trỏ vào chart và config của `dev`).

## Verify

Trước sync:

```bash
python3 week03/day14/verify-release.py week03/day14/config/environments/dev
week03/day15/scope-check.sh <commit> <path được phép>
```

Sau sync:

```bash
kubectl -n dev rollout status deploy/app
kubectl -n dev get pod,endpointslice
kubectl -n dev logs deploy/app
# smoke test đi qua Service, không chỉ nhìn Pod Ready
kubectl -n dev port-forward svc/app 8081:80 & curl -fsS http://localhost:8081/
```

Đọc lỗi theo lớp: `ImagePullBackOff` (image) · `CrashLoopBackOff` (config/app, xem `logs --previous`) · `Pending` (scheduling, xem Events) · `Running 0/1` (readiness) · `Running 1/1` nhưng gọi lỗi (Service/traffic). Chi tiết ở `week03/day16`–`18`.

## Retry

- CI fail: `gh run view <run-id> --log-failed`, sửa nguyên nhân, push lại; không rerun mù khi chưa đọc log.
- Sync fail: đọc message → resource lỗi → `describe`/events → sửa trong Git → sync lại.

## Rollback

Rollback là một commit trên Git, không phải lệnh trên cluster:

```bash
git revert <commit lỗi>        # hoặc đặt lại image tag trước đó trong releases.yaml
# PR → merge → ArgoCD sync → verify lại như trên
```

`kubectl rollout undo` không dùng với app do ArgoCD quản lý vì Git vẫn giữ tag mới, sẽ thành drift.

## Quy ước

- Commit message mô tả đúng thay đổi (`feat:`, `fix:`, `docs:`, `ci:`...); sửa sai bằng `git revert`, không viết lại lịch sử đã push.
- Mọi thay đổi qua PR; trước khi deploy lên stag/prod điền checklist ở `week03/day15/pre-deploy-checklist.md`.
- Không commit secret; env nhạy cảm đi qua Secret/ExternalSecret.

# Day 14 — Verification, bad release & rollback

Làm trên env `dev` thu nhỏ ở `week03/day14/config/environments/dev` (copy từ day 9, dùng chung chart `week02/day09/charts/app`).
Không sửa `week02/day09` vì Application ArgoCD ở day 10 đang trỏ vào path đó.

## Luồng verify sau release

```
Git (releases.yaml / values.yaml) → ArgoCD sync → Deployment → ReplicaSet mới → Pod Ready → Endpoint → Service → request
```

| Bước | Kiểm tra | Lỗi nếu sai |
|---|---|---|
| Trước sync | tag có trong registry, env bắt buộc có giá trị, port probe khớp | chặn được ngay ở PR |
| ArgoCD | `Synced` / `Healthy` | `OutOfSync`, `Degraded`, `Progressing` mãi |
| Rollout | `kubectl rollout status`, ReplicaSet mới scale lên | Pod mới không Ready, RS cũ vẫn giữ |
| Pod | `get pod`, `logs`, `describe` (Events) | `ImagePullBackOff`, `Exited (1)`, `0/1` |
| Traffic | EndpointSlice `ready=true`, smoke test `curl` | Service không có endpoint |

Synced/Healthy chưa đủ: đã thấy ở day 9 là readiness sai port thì Pod vẫn `Running` nhưng `0/1`, nên phải nhìn tới endpoint và gọi thử app.

## Script verify (`verify-release.py`)

Máy lab không cần helm/cluster: script gộp values theo thứ tự helm (chart → env `values.yaml` → `releases.yaml`) rồi check 3 lớp lỗi:

| Lớp | Check | Ngoài cluster sẽ thấy |
|---|---|---|
| image | tag trong `releases.yaml` có trong `registry-tags.txt` (`1.0.0`, `1.1.0`, `sha-c4ab653` — các tag đã push ở day 7, 8) | `ErrImagePull` → `ImagePullBackOff` |
| config | env `GREETING` có giá trị (app.py bắt buộc) | container `Exited (1)` / `CrashLoopBackOff` |
| traffic | port probe == `containerPort` (8080) | Pod `Running 0/1`, endpoint `ready=false` |

```bash
python3 week03/day14/verify-release.py week03/day14/config/environments/dev
```

## Lab: 3 release lỗi có kiểm soát

Mỗi lần: 1 commit lỗi → chạy verify (detect + xác định lớp) → `git revert` → verify lại.

| # | Commit lỗi | Thay đổi | verify | Lớp | Revert |
|---|---|---|---|---|---|
| 1 | `d464513` | `releases.yaml` tag `1.1.0` → `1.2.0` | `FAIL [image] tag '1.2.0' không có trong registry` | image | `8aa59e3` |
| 2 | `3fc6962` | `values.yaml` `GREETING: ""` | `FAIL [config] env GREETING thiếu hoặc rỗng` | config / runtime | `f060bd7` |
| 3 | `736ea2e` | thêm `readinessProbe` port `9999` | `FAIL [traffic] readinessProbe port 9999 != containerPort 8080` | traffic | `bc9d548` |

Sau mỗi revert verify về `PASS image / config / traffic`. `git diff eb9b3a4 HEAD` rỗng → desired state quay về đúng baseline `eb9b3a4`.

### Kiểm chứng lỗi runtime với app thật (`week02/day06/app.py`)

| Thử | Kết quả |
|---|---|
| Chạy không có `GREETING` | in `ERROR: GREETING env is required`, exit code 1 |
| Chạy `GREETING=hello from dev` | in `GREETING`, `APP_VERSION`, `PID`, nghe 8080 |
| `curl localhost:8080` | HTTP 200 |
| `curl localhost:9999` | không kết nối được (curl exit 7, connection refused) |

Khớp với bảng lớp lỗi: app chết vì config, hoặc app sống nhưng gọi sai port thì vẫn không có traffic — giống bài sai port ở day 7.

## Rollback

| Cách | Khi nào | Lịch sử |
|---|---|---|
| `git revert <commit lỗi>` | release lỗi đã vào Git | giữ cả lỗi và cách sửa, ArgoCD sync lại về trạng thái cũ |
| Sửa `releases.yaml` về tag trước (vd `1.1.0`) | chỉ đổi image | 1 dòng diff, dễ review |
| `kubectl rollout undo` | **không dùng** với app do ArgoCD quản lý | Git vẫn là tag mới → drift, selfHeal đè lại |

Thứ tự rollback: revert trên Git → PR → merge → ArgoCD sync → verify lại 5 bước ở bảng đầu.

## Issue

Lần chạy đầu 3 bad release chồng lên nhau, revert không tạo ra commit nào, verify vẫn FAIL cả 3 lớp.
Root cause: `git revert -q` không có option `-q` ở bản git này, lệnh báo usage rồi dừng, script vẫn chạy tiếp nên các commit lỗi dồn lại. Bỏ `-q`, redirect output; làm lại từ `eb9b3a4` thì mỗi lỗi có một cặp commit lỗi + revert như bảng trên.

## Bài học

- Lỗi nên bị chặn ở PR (verify trước sync) hơn là phát hiện sau khi Pod đã chết.
- Mỗi lớp lỗi có một dấu hiệu riêng (ImagePullBackOff / Exited 1 / 0/1), nhìn đúng chỗ thì xác định lớp rất nhanh.
- Rollback là một commit trên Git, không phải lệnh trên cluster.

# Traceability — Ngày 2 (22/09/2026)

## Chuỗi trace trong lab

```
dòng code → commit → PR → task
```

| Bước | Lệnh | Kết quả |
|---|---|---|
| Dòng code → commit | `git blame -L 5,5 week01/day02/service.yaml` | `eb7966e` |
| File → mọi commit đã đổi nó | `git log --oneline -- week01/day02/service.yaml` | `eb7966e`, `59c9a29`, `55c25b2` |
| Commit → PR | `gh pr list --state merged --json number,mergeCommit` | `55c25b2` thuộc PR #1, merge `eece9c0` |
| Commit → nội dung đổi gì | `git show 59c9a29` | `targetPort: 8080` → `3000` |

## Lịch sử Ngày 2

| Commit | Nội dung | Ghi chú |
|---|---|---|
| `55c25b2` | feat: add Service manifest | qua PR #1, có self-review |
| `eece9c0` | Merge PR #1 | merge commit, 2 parent |
| `59c9a29` | fix: change targetPort to 3000 | **commit lỗi** — push thẳng main, không qua PR |
| `eb7966e` | Revert `59c9a29` | rollback, giữ nguyên lịch sử |

## Chuỗi tương ứng trong repo thật (devops-deployments)

```
task → PR (repo app) → commit → CI build → image tag → GitOps PR → ArgoCD sync → Pod
```

Ví dụ tag `prod-cfd-th-b642a27-206`:

| Phần | Ý nghĩa | Trace được gì |
|---|---|---|
| `prod-cfd` | environment | biết đang chạy ở env nào |
| `th` | country | biết deployment nào |
| `b642a27` | git commit SHA của repo app | `git show b642a27` → code đang chạy |
| `206` | CI build number | log Jenkins của build đó |

Từ Pod đang chạy → `kubectl describe pod` lấy image tag → SHA → commit → PR → task.

## Bài học

- Commit message mô tả đúng thay đổi thì `git log --oneline` là công cụ trace, không cần mở GitHub.
- Push thẳng main (`59c9a29`) làm mất một mắt xích: không có PR, không ai review, không có mô tả "tại sao".
- Revert giữ cả lỗi lẫn cách sửa trong lịch sử — đọc lại biết chuyện gì đã xảy ra. Force push thì mất luôn.

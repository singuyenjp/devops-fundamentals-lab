# Day 16 — Troubleshooting CI failure

Pipeline lab: `.github/workflows/day16-ci.yml` (chạy trên branch `feature/day16-ci-failure`).

```
push ──► lint-manifest   (yq đọc manifest)
    ├──► build           (docker build week03/day16/app)
    └──► smoke           (needs: build) docker run -e GREETING + curl :8080
```

Baseline xanh ở commit `49444c2` (run `38393885553`). Mỗi case: 1 commit làm hỏng → đọc log → xác định root cause → `git revert` → xanh lại.

## Cách trace

`run → job nào fail → step nào fail → đọc log từ lỗi đầu tiên → root cause sơ bộ → mới fix`

```bash
gh run list --branch <branch>
gh run view <run-id>              # job / step nào fail
gh run view <run-id> --log-failed # log của step fail
```

## Case 1 — lint-manifest fail

| | |
|---|---|
| Commit lỗi | `e0cfc7f` "fix: tidy deployment metadata" (run `38393978089`) |
| Job / step | `lint-manifest` / `Validate manifest syntax` |
| Log | `bad file 'week03/day16/manifests/deployment.yaml': ... did not find expected key` (L1–L5) |
| Hypothesis | YAML sai cú pháp ở đầu file, chưa phải lỗi nội dung Deployment |
| Root cause | commit làm lệch indent `metadata.name` và `labels` → mapping không còn cùng cấp |
| Fix | revert `47562eb` → run `38394078494` xanh |

Quan sát: `build` và `smoke` vẫn xanh vì không có `needs` với `lint-manifest`. Muốn lint chặn build thì phải khai `needs`.

## Case 2 — build fail

| | |
|---|---|
| Commit lỗi | `b2f3251` "refactor: rename app entrypoint to main.py" (run `38394083969`) |
| Job / step | `build` / `Build image` |
| Log | `failed to compute cache key: ... "/main.py": not found` |
| Hypothesis | Dockerfile `COPY` file không có trong build context |
| Root cause | commit đổi `COPY app.py` → `COPY main.py` (và `.dockerignore`) nhưng file trong repo vẫn là `app.py` |
| Fix | revert `11403f5` → run `38394222039` xanh |

Quan sát: `smoke` ở trạng thái **skipped** vì `needs: build`. Log dòng đầu là bước load context (`transferring context: 2B`), lỗi thật nằm ở cuối: đọc từ dòng `ERROR` đầu tiên, không đọc hết.

## Case 3 — smoke fail (build vẫn xanh)

| | |
|---|---|
| Commit lỗi | `2542b0e` "ci: pass greeting env to smoke test container" (run `38394227116`) |
| Job / step | `smoke` / `Run container and call it` |
| Log | `ERROR: GREETING env is required` rồi `curl: (7) Failed to connect to localhost port 8080` |
| Hypothesis | lỗi curl chỉ là hệ quả; container chết ngay lúc start (giống day 7: thiếu env → exit 1) |
| Root cause | workflow truyền `-e GREETINGS=hello` (thừa chữ S), app đọc `GREETING` → thoát |
| Fix | revert `d27b53b` → run `38394337946` xanh |

Quan sát: step fail là `curl` (exit 7) nhưng root cause nằm ở dòng log in ra trước đó bởi `docker logs app`. Nếu workflow không có `docker logs` thì chỉ thấy connection refused, không biết vì sao. Image không có lỗi, lỗi ở cách CI chạy nó.

## Case Pending (runtime, không phải app crash)

Phân tích theo tài liệu Kubernetes, để phân biệt với 3 case trên.

| Symptom | Event / dấu hiệu | Hypothesis | Root cause sơ bộ |
|---|---|---|---|
| Pod `Pending`, `kubectl logs` không có gì | `FailedScheduling: 0/N nodes are available: ... Insufficient cpu` | `requests` lớn hơn phần còn lại của node | scheduler chọn node theo **requests**, không theo usage; không node nào đủ chỗ |
| Pod `Pending` | `... node(s) didn't match Pod's node selector/affinity` | `nodeSelector` / affinity không khớp label node | label không tồn tại trên node nào |
| Pod `Pending` | `... node(s) had untolerated taint` | node có taint, Pod thiếu toleration | cấu hình toleration |

Phân biệt nhanh theo trạng thái Pod:

| Trạng thái | Pod đã có node chưa | Đọc ở đâu |
|---|---|---|
| `Pending` + `FailedScheduling` | chưa | `kubectl describe pod` → **Events** (không có container nên không có log) |
| `ImagePullBackOff` | rồi | Events (`Failed to pull image`) |
| `CrashLoopBackOff` / `Exited (1)` | rồi, container đã chạy | `kubectl logs` / `--previous` |

Điểm khác với CI fail: pipeline xanh vẫn có thể ra Pod `Pending`, vì CI chỉ build/push, còn lỗi lịch là việc của scheduler sau khi sync.

## Issue

Chưa gặp lỗi ngoài các case cố ý. Lúc viết step lint em đã định dùng `kubectl apply --dry-run=client`, nhưng thử ở local thấy lệnh này vẫn gọi tới API server (`connection refused`) nên đổi sang `yq` — chỉ kiểm tra cú pháp YAML, không kiểm tra nội dung Deployment.

## Bài học

- Đọc theo thứ tự job → step → log, bắt đầu từ lỗi đầu tiên; lỗi cuối (curl exit 7) thường chỉ là hệ quả.
- Cần `docker logs` trong CI, không có thì mất evidence.
- `needs` quyết định job sau skip hay vẫn chạy; xanh một job không có nghĩa cả pipeline đúng.
- Fix bằng revert commit làm hỏng, không sửa tay rồi push đè.

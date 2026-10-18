# Day 18 — Runtime troubleshooting, AI usage & escalation

Workflow: `.github/workflows/day18-runtime.yml` (branch `feature/day18-runtime-troubleshooting`). Manifest ở `week03/day18/manifests/`.

```
CI: build image ──► kind cluster + load image ──► apply manifests ──► rollout status ──► smoke qua Service
    (xanh)                                          (deploy)           (healthy?)         (traffic?)
```

Ở cả 3 case dưới đây bước **CI - build image luôn xanh**, lỗi nằm ở các bước sau. Vì vậy:

| | Câu hỏi | Bằng chứng |
|---|---|---|
| CI success | image build được không | step build xanh |
| Deploy success | object có được tạo và chạy không | `rollout status`, Pod `READY` |
| App healthy | app nhận traffic đúng không | smoke test qua Service |

Baseline: commit `41a3cba`, run `39128015573`, cả 3 mức đều xanh (`HTTP 200`).

## 3 case

| # | Commit lỗi | Run | Step fail | Trạng thái | Lớp |
|---|---|---|---|---|---|
| 1 | `9d7f8d4` bỏ env `GREETING` | `39128128318` | Wait for rollout | Pod `CrashLoopBackOff` | config / runtime |
| 2 | `e453f37` `requests.cpu: "64"` | `39128298237` | Wait for rollout | Pod `Pending`, chưa có node | scheduling |
| 3 | `7fdd3cf` Service `targetPort: 9090` | `39128449586` | Smoke test | Pod `1/1 Running` nhưng gọi Service lỗi | traffic |

Revert tương ứng: `3b9fcba`, `02abf3d`, `97c5d90` (run `39128447809` cho case 2 xanh).

### Case 1 — CrashLoopBackOff
- Deployment `0/1`, Pod `CrashLoopBackOff` (3 restart). Events: image đã có trên node, container `Created` / `Started`, rồi `Readiness probe failed: ... connection refused`, `Back-off restarting failed container`.
- Log container (`logs --previous`): `ERROR: GREETING env is required`.
- Root cause: manifest thiếu env `GREETING`, app thoát ngay nên chưa kịp mở port 8080 → probe bị từ chối kết nối. Lỗi probe chỉ là hệ quả.

### Case 2 — Pending
- Pod `Pending`, `IP <none>`, `NODE <none>`; EndpointSlice không có endpoint.
- Events chỉ có `FailedScheduling: 0/1 nodes are available: 1 Insufficient cpu`. Không có log vì container chưa từng chạy.
- Root cause: `requests.cpu: "64"` lớn hơn CPU còn lại của node. Scheduler chỉ nhìn `requests`, không nhìn mức dùng thực tế.

### Case 3 — Pod khoẻ nhưng traffic hỏng
- Deployment `1/1`, Pod `1/1 Running`, ngay cả EndpointSlice cũng có endpoint `10.244.0.5`. Nhìn riêng từng object thì không thấy lỗi.
- Điểm khác thường: EndpointSlice cổng **9090** trong khi container nghe **8080**. Smoke test: `Forwarding from 127.0.0.1:8081 -> 9090`, rồi `lost connection to pod`, curl `Empty reply`.
- Root cause: `targetPort` của Service trỏ sai cổng. Readiness probe gọi thẳng vào Pod (8080) nên vẫn pass, không bắt được lỗi này.

Từ case 3: Pod `Ready` chưa đủ, phải có smoke test đi qua Service mới biết traffic thông.

## Phân lớp nhanh

| Dấu hiệu | Lớp | Xem ở đâu |
|---|---|---|
| `Pending`, `FailedScheduling` | scheduling | Events của Pod |
| `ErrImagePull` / `ImagePullBackOff` | image (day 17) | Events |
| `CrashLoopBackOff`, `Exited (1)` | app / config | `logs --previous` |
| `Running 0/1` | readiness | Events `Readiness probe failed` |
| `Running 1/1` nhưng gọi lỗi | traffic | EndpointSlice (port), selector, smoke qua Service |

## Dùng AI (Claude Code) để đọc log

Quy trình: đưa log/Events cho AI → AI đề xuất giả thuyết → mình kiểm chứng bằng log hoặc `kubectl` → chỉ sửa khi có bằng chứng.

| Case | Giả thuyết AI đưa ra | Kiểm chứng | Kết quả |
|---|---|---|---|
| 1 | Image không pull được | Events: `already present on machine`, `Created`, `Started` | Loại |
| 1 | Probe sai cổng nên Pod không Ready | Probe bị từ chối vì app đã thoát; log container nói rõ lý do | Chỉ là hệ quả, loại |
| 1 | Thiếu env bắt buộc | `logs --previous`: `GREETING env is required`, khớp `app.py` | Xác nhận |
| 2 | Pod crash | Pod chưa có node, không có container, không có log | Loại |
| 2 | Node không đủ CPU theo `requests` | Event `Insufficient cpu`, khớp `requests.cpu: "64"` | Xác nhận |
| 3 | Pod chưa Ready | `1/1 Running` | Loại |
| 3 | Selector Service sai | EndpointSlice có endpoint | Loại |
| 3 | `targetPort` sai | EndpointSlice cổng 9090 ≠ containerPort 8080; port-forward tới 9090 lỗi | Xác nhận |

Quy tắc: AI chỉ đề xuất, mỗi giả thuyết phải có một dòng log/Event làm bằng chứng; không apply đề xuất chưa kiểm chứng; không đưa secret hay dữ liệu thật vào prompt.

## Khi nào tự sửa, khi nào escalate

| Tự sửa | Escalate (dừng và báo) |
|---|---|
| Lỗi nằm trong file mình được giao, có evidence rõ (case 1, case 3) | Cần quyền / tài nguyên ngoài scope: thêm node, đổi quota, đụng prod |
| Fix qua Git, revert được | Đã thử nhưng không rõ root cause, hoặc không chắc rollback |
| Môi trường lab / dev | Có nguy cơ ảnh hưởng người dùng thật |

Case 2 phụ thuộc ý định: nếu `64` là gõ nhầm thì tự sửa trong Git; nếu app thật sự cần chừng đó CPU thì phải thêm capacity cho cluster nên phải escalate. Bản nháp tin nhắn ở `escalation-message.md`.

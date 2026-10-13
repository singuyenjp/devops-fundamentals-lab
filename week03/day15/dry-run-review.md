# Day 15 — Dry-run review một change

Áp checklist trong `pre-deploy-checklist.md` lên change ở lab (chỉ review, không deploy). Công cụ: `scope-check.sh`, `week03/day14/verify-release.py`.

## Review 1 — release lỗi ở day 14 (`d464513`)

`release(dev): update image tag to 1.2.0` — đổi `releases.yaml` của dev từ `1.1.0` lên `1.2.0`.

| Mục | Kiểm tra | Kết quả |
|---|---|---|
| Scope | `./scope-check.sh d464513 week03/day14/config/environments/dev` | PASS — chỉ có `.../dev/releases.yaml` |
| Approval | dev, thay đổi tự review trong lab | đủ cho dev; stag/prod thì cần reviewer khác |
| Risk | đổi image tag ở dev, chỉ ảnh hưởng 1 Pod dev | thấp |
| Verify (trước sync) | `verify-release.py` | **FAIL** `[image] tag '1.2.0' không có trong registry` |
| Rollback | revert `d464513` hoặc đặt lại tag `1.1.0` | rõ, 1 dòng |

**Quyết định: KHÔNG merge.** Scope và risk ổn nhưng verify fail: `1.2.0` chưa được build/push, deploy sẽ ra `ImagePullBackOff`. Làm lại: build + push `1.2.0` → thêm vào registry → mới đổi tag.

## Review 2 — dự định promote lên stag (không commit)

Giả định đổi `week02/day09/config/environments/stag/releases.yaml`: tag `1.0.0` → `1.1.0` (đưa bản đã chạy ở dev sang stag).

| Mục | Kiểm tra | Kết quả |
|---|---|---|
| Scope | diff 1 dòng ở `stag/releases.yaml`, không đụng `dev`, chart, `values.yaml` | đúng scope |
| Approval | stag | cần reviewer approve trên PR trước khi merge |
| Risk | stag 2 replicas, rolling update; đổi chỉ là image tag, `1.1.0` đã chạy ổn ở dev | thấp–vừa |
| Verify (trước sync) | `verify-release.py` trên stag với tag `1.1.0` | PASS image / config / traffic |
| Verify (sau sync) | ArgoCD `Synced/Healthy`, `rollout status`, 2 Pod `1/1`, endpoint ready, `curl` thấy `APP_VERSION = 1.1.0` | liệt kê sẵn để làm khi deploy |
| Rollback | đặt lại tag `1.0.0` (hoặc revert PR) → sync → verify lại | rõ |

**Quyết định: được phép tạo PR**, chờ approve rồi mới merge. Không tự merge, không sync tay.

## Thử kiểm tra scope trên lịch sử lab

| Commit | Scope cho phép | Kết quả |
|---|---|---|
| `d464513` (day 14 bad release) | `week03/day14/config/environments/dev` | PASS |
| `64f1a05` chore(dev): update image tag to 1.1.0 | `week02/day09/config/environments/dev` | FAIL — có thêm `week02/day09/environments.md` (file tài liệu, không phải config deploy → chấp nhận được nhưng phải nói rõ trong PR) |
| `8d7d4c7` feat: add dev and stag environments | `week02/day09/config/environments/dev` | FAIL — đổi cả chart và stag, đúng là change lớn hơn "chỉ dev" |

Check scope bằng script bắt được ngay thay đổi vượt phạm vi, không phải tự đọc từng file.

## Bài học

- Scope + risk ổn chưa đủ; verify fail thì vẫn phải dừng.
- Approval là bước riêng, không thay bằng việc "tự thấy ổn".
- Rollback plan phải viết **trước** khi merge, không đợi lỗi mới nghĩ.
- Càng gần prod càng phải làm đủ checklist, dev thì thử sai được nhưng vẫn qua PR.

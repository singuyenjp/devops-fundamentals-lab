# Day 15 — Release safety: pre-deploy checklist

Mục tiêu: trước khi đổi bất cứ thứ gì ở env thật phải trả lời được 5 câu: **đổi gì (scope), ai cho phép (approval), nguy hiểm gì (risk), kiểm tra sao (verify), quay lại sao (rollback)**.

## Nguyên tắc

- Chỉ làm trong scope được giao. Thấy thứ khác cần sửa thì ghi lại, hỏi lại, không tự sửa kèm.
- Env càng gần production thì càng cần approval rõ và càng ít được thử.
- Không chắc thì dừng và hỏi, không thử bừa trên env thật.
- Mọi thay đổi đi qua Git + PR; không `kubectl edit/patch/scale` trên resource do ArgoCD quản lý (day 12).

## Checklist pre-deploy

### 1. Scope

- [ ] Task/ticket nói rõ đổi gì, ở env nào, app nào.
- [ ] Diff chỉ chứa file thuộc scope: `scope-check.sh <commit> <path env>` → PASS.
- [ ] Không đụng env khác (đổi dev thì stag/prod không có trong diff).
- [ ] Không có file lạ (secret, file tạm, đổi lan sang chart dùng chung).

### 2. Approval

- [ ] Có PR, có người review khác tác giả (self-review chỉ để luyện tập, không thay approval).
- [ ] Env stag/prod: người có quyền duyệt đã approve trong PR, không approve miệng.
- [ ] Prod: có cửa sổ deploy được đồng ý, không deploy ngoài giờ/ngoài scope khi chưa có xác nhận.

### 3. Risk

- [ ] Mức ảnh hưởng nếu lỗi: 1 Pod / 1 env / toàn bộ người dùng.
- [ ] Loại thay đổi: chỉ đổi image tag (thấp) / đổi config-env (vừa, cần rollout) / đổi chart, ingress, secret (cao).
- [ ] Có gì không rollback được không (migration DB, xoá dữ liệu, đổi secret đã dùng).
- [ ] Việc phụ thuộc đã sẵn sàng (image đã push, key AWS đã tạo, cert đã có) — giống thứ tự release ở day 13.

### 4. Verify

- [ ] Trước sync: `verify-release.py` PASS (image tồn tại, env đủ, port khớp).
- [ ] Sau sync: ArgoCD `Synced/Healthy`, `rollout status` xong, Pod `1/1`, log không lỗi.
- [ ] Traffic: endpoint `ready=true`, smoke test (`curl`) trả đúng version.
- [ ] Đã biết dấu hiệu "xấu" để dừng: ImagePullBackOff, CrashLoopBackOff, Pod `0/1`, 5xx tăng.

### 5. Rollback

- [ ] Biết commit/tag trước đó (vd tag cũ `1.1.0`, commit trước).
- [ ] Cách rollback là `git revert` hoặc đặt lại tag cũ qua PR, không sửa tay cluster.
- [ ] Biết ai có quyền merge/sync rollback và mất bao lâu.
- [ ] Rollback cũng phải verify lại bằng đúng các bước ở mục 4.

## Khác nhau giữa các env

| | dev | stag | prod |
|---|---|---|---|
| Ai được đổi | tự đổi qua PR trong scope | PR + reviewer approve | PR + approver có quyền + change window |
| Verify tối thiểu | verify script + smoke | verify + smoke + so với dev | verify + smoke + theo dõi sau deploy |
| Rollback | revert, chấp nhận thử sai | revert, báo lại team | có sẵn plan trước khi merge, ưu tiên rollback sớm |
| Thử nghiệm | được | hạn chế | không |

## Khi nào dừng và hỏi

- Diff có file ngoài scope mà không giải thích được.
- `verify` FAIL hoặc không chắc kết quả.
- Chưa có approval nhưng đã sắp merge.
- Không biết rollback thế nào.
- Việc cần quyền/secret mình không có.

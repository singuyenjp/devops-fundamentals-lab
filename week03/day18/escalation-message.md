# Escalation message (bản nháp, case 2 — Pod Pending)

Dùng khi lỗi vượt scope: cần thêm capacity cho cluster, mình không có quyền và không nên tự thử trên môi trường thật.

---

**Anh/chị ơi, em cần hỗ trợ về Pod `app` bị `Pending` ở namespace `runtime-lab`.**

**Hiện trạng:** Deployment `app` 0/1, Pod `Pending`, chưa được gán node. CI build image xanh, lỗi xảy ra sau khi deploy.

**Evidence:**
- Event: `FailedScheduling: 0/1 nodes are available: 1 Insufficient cpu`
- Manifest đang request `cpu: "64"` (commit `e453f37`), run `39128298237`
- Pod chưa có container nên không có log

**Em đã làm:** đọc Events, so `requests` với CPU của node, xác nhận root cause là `requests` lớn hơn phần còn lại của node; revert commit để quay về trạng thái chạy được (`02abf3d`).

**Chưa chắc / cần quyết định:** giá trị `64` có phải do em gõ nhầm hay app thật sự cần chừng đó CPU. Nếu cần thật thì phải tăng capacity hoặc đổi loại node — việc này em không có quyền và không tự thử.

**Em cần anh/chị:** xác nhận mức CPU hợp lý cho app, hoặc quyết định có tăng capacity không.

**Ảnh hưởng:** chỉ môi trường lab, chưa ảnh hưởng người dùng. Trong lúc chờ em giữ bản đã revert.

**Bước tiếp theo:** có xác nhận thì em sửa `requests` trong Git, tạo PR rồi sync và verify lại.

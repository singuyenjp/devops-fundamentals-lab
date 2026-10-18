# Evidence index

Bảng này dùng để lần ngược: **task → PR → commit → pipeline run → image tag → release**. Chỉ gồm phần làm trong repo lab; phần làm trong repo công ty (ngày 3, 4, 5, 11, 12, 13) được ghi ở Daily Log, không đưa vào repo này.

## Tuần 1

| Ngày | Nội dung | PR | Commit / evidence chính |
|---|---|---|---|
| 1 | Git basics, branch, conflict, rebase | — | merge conflict `48226e1`; rebase `78fe8cb → d3587e8`; branch `feature/rebase-demo`; ảnh `week01/day01/evidence/` |
| 2 | PR, revert, traceability | #1, #2 | merge `eece9c0` (#1), `9adabd8` (#2); commit lỗi `59c9a29` → revert `eb7966e`; `week01/day02/TRACEABILITY.md` |

## Tuần 2

| Ngày | Nội dung | PR | Commit / evidence chính |
|---|---|---|---|
| 6 | Dockerfile, build, tag | #3 | `c4ab653`; tag `1.0.0` + `sha-c4ab653` cùng một image |
| 7 | Registry, lỗi build/auth/push | #4 | `8b81390`; `week02/day07/registry-errors.md` |
| 8 | Desired state, manifest | #5 | `2c0e470`, `5c03952`; `week02/day08/desired-state.md` |
| 9 | Env dev/stag, image update, probe | #6 | `8d7d4c7`, `64f1a05` (tag dev `1.0.0 → 1.1.0`); `week02/day09/environments.md` |
| 10 | ArgoCD, sync, selfHeal | #7 | `371c28c`; `week02/day10/argocd/app-dev.yaml`, `argocd-flow.md` |

## Tuần 3

| Ngày | Nội dung | PR | Commit / pipeline run |
|---|---|---|---|
| 14 | Verify, bad release, rollback | #8 | baseline `eb9b3a4`; lỗi → revert: `d464513 → 8aa59e3` (image), `3fc6962 → f060bd7` (config), `736ea2e → bc9d548` (traffic) |
| 15 | Release safety, checklist | #9 | `f5076dc`; `week03/day15/` |

## Tuần 4

| Ngày | Nội dung | PR | Commit / pipeline run |
|---|---|---|---|
| 16 | Troubleshooting CI | #10 | baseline run `38393885553`; lỗi → revert: `e0cfc7f → 47562eb` (run `38393978089`), `b2f3251 → 11403f5` (run `38394083969`), `2542b0e → d27b53b` (run `38394227116`) |
| 17 | Troubleshooting GitOps sync | #11 | baseline run `38394559282`; `d6f6152 → 8e9fe94` (run `38394735456`), `523ec7f → 71cc8d6` (`38394916336`), `750af60 → 344d8ea` (`38395060755`), `cad3936 → d2900e6` (`38395236545`) |
| 18 | Runtime troubleshooting, escalate | #12 | baseline run `39128015573`; `9d7f8d4 → 3b9fcba` (run `39128128318`), `e453f37 → 02abf3d` (`39128298237`), `7fdd3cf → 97c5d90` (`39128449586`) |
| 19 | README, evidence index | #13 | file này và `README.md` |
| 20 | Final exercise, demo | #14 | xem `week03/day20/` |

Xem run: `gh run view <run-id> --log` hoặc `https://github.com/singuyenjp/devops-fundamentals-lab/actions/runs/<run-id>`.

## Ví dụ lần ngược một thay đổi

Ngày 17, case image tag không tồn tại:

| Bước | Là gì | Lấy ở đâu |
|---|---|---|
| Task | luyện trace SyncFailed/Degraded | `week03/day17/sync-failure-notes.md` |
| PR | #11 | `gh pr view 11` |
| Commit | `cad3936` đổi `releases.yaml` tag `1.27-alpine → 9.9.9` | `git show cad3936` |
| Pipeline | run `38395236545`, step `Health (rollout status)` fail | `gh run view 38395236545` |
| Image | `nginxinc/nginx-unprivileged:9.9.9` không tồn tại | event `Failed to pull image ... NotFound` |
| Release / rollback | revert `d2900e6`, run `38395508506` xanh | `git show d2900e6` |

Quy tắc tag lab: `sha-<commit>` (ngày 6–7) hoặc `X.Y.Z` kèm label `org.opencontainers.image.revision` trong image, để từ image lần về đúng commit.

## Tự kiểm tra

- Từ một commit có biết PR nào? `gh pr list --state merged --search <sha>` hoặc `git log --merges --ancestry-path <sha>..main`.
- Từ một run biết commit nào? `gh run view <run-id> --json headSha`.
- Từ tag image biết commit nào? Phần `sha-xxxx` hoặc label revision.

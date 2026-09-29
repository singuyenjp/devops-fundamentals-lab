# Day 7 — Registry push/pull & phân biệt lỗi

Registry: `registry:2` chạy local ở `localhost:5000`, bật auth htpasswd.
Image: `day06-app` build từ commit `c4ab653`.

## Push / pull

```powershell
docker build --build-arg APP_VERSION=1.0.0 --label org.opencontainers.image.revision=<full sha> -t localhost:5000/day06-app:sha-c4ab653 .
docker login localhost:5000
docker push localhost:5000/day06-app:sha-c4ab653
docker rmi localhost:5000/day06-app:sha-c4ab653
docker pull localhost:5000/day06-app:sha-c4ab653
docker inspect localhost:5000/day06-app:sha-c4ab653 --format '{{index .Config.Labels "org.opencontainers.image.revision"}}'
```

Digest: `sha256:57bdfabf9758...`. Label trong image ra đúng commit `c4ab653`.

## Các loại lỗi

| Loại | Cách tạo | Lỗi |
|---|---|---|
| Build fail | `COPY main.py` (file không có) | `"/main.py": not found` |
| Auth fail | push/pull khi chưa login | `no basic auth credentials` |
| Auth fail | login sai mật khẩu | `401 Unauthorized` |
| Push fail | push tag không có ở local | `tag does not exist` |
| Image not found | pull sai tag / sai repo | `...:1.0.1: not found` |
| Sai registry | pull `localhost:5001` | `dial tcp ... i/o timeout` |

## Runtime sau khi pull

| Lỗi | Thấy gì | Root cause |
|---|---|---|
| Thiếu env | `Exited (1)`, log `ERROR: GREETING env is required` | không truyền `-e GREETING` |
| Sai port | container `Up`, curl lỗi | map `-p 18081:80` nhưng app nghe 8080 |

Pull được image → registry/auth ổn. Container không lên hoặc không gọi được → xem logs, env, port trước.

#!/usr/bin/env python3
"""Verify một env trước khi sync (chạy được khi không có helm/cluster).

Gộp values theo đúng thứ tự helm: chart values.yaml <- env values.yaml <- env releases.yaml,
rồi kiểm tra 3 lớp lỗi hay gặp của một bad release:

  image   : tag trong releases.yaml có trong registry không (ImagePullBackOff)
  config  : env bắt buộc của app (app.py: GREETING) có giá trị không (container Exited 1)
  traffic : port của probe có khớp containerPort không (Pod 0/1, Service không có endpoint)

Dùng: python3 verify-release.py config/environments/dev
Exit code 0 = pass, 1 = có lỗi.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHART_VALUES = HERE / "../../week02/day09/charts/app/values.yaml"
REGISTRY_TAGS = HERE / "registry-tags.txt"
REQUIRED_ENV = ["GREETING"]  # app.py thoát exit 1 nếu thiếu


def parse_yaml(path):
    """Parse YAML tối giản (map lồng nhau + scalar) - đủ cho values/releases của lab."""
    root = {}
    stack = [(-1, root)]
    for raw in Path(path).read_text().splitlines():
        line = raw.split(" #")[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        key, _, val = line.strip().partition(":")
        val = val.strip()
        while stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if val == "":
            parent[key] = {}
            stack.append((indent, parent[key]))
        elif val == "{}":
            parent[key] = {}
        else:
            parent[key] = val.strip('"').strip("'")
    return root


def merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            merge(base[k], v)
        else:
            base[k] = v
    return base


def main(env_dir):
    env_dir = Path(env_dir)
    values = parse_yaml(CHART_VALUES)
    for f in ("values.yaml", "releases.yaml"):
        merge(values, parse_yaml(env_dir / f))

    errors = []

    tag = values["image"]["tag"]
    known = REGISTRY_TAGS.read_text().split()
    if tag not in known:
        errors.append(("image", f"tag '{tag}' không có trong registry (có: {', '.join(known)})"))

    env = values.get("env", {})
    for name in REQUIRED_ENV:
        if not env.get(name):
            errors.append(("config", f"env {name} thiếu hoặc rỗng -> app exit 1 lúc start"))

    cport = values["containerPort"]
    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
        port = values.get(probe, {}).get("httpGet", {}).get("port")
        if port and port != cport:
            errors.append(("traffic", f"{probe} port {port} != containerPort {cport} -> Pod 0/1, không có endpoint"))

    print(f"env={env_dir}  image=day06-app:{tag}  replicas={values['replicaCount']}  containerPort={cport}")
    if errors:
        for layer, msg in errors:
            print(f"FAIL [{layer}] {msg}")
        return 1
    print("PASS image / config / traffic")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "config/environments/dev"))

#!/usr/bin/env bash
# Kiểm tra 1 commit có nằm trong scope (path được phép) hay không.
# Dùng: ./scope-check.sh <commit> <allowed-path-prefix>
set -u
commit="$1"; allowed="$2"
echo "commit $(git log -1 --format='%h %s' "$commit")"
out=0
for f in $(git diff-tree --no-commit-id --name-only -r "$commit"); do
  case "$f" in
    "$allowed"*) echo "  in-scope   $f" ;;
    *)           echo "  OUT-SCOPE  $f"; out=1 ;;
  esac
done
[ $out -eq 0 ] && echo "=> PASS" || echo "=> FAIL: có file ngoài scope"
exit $out

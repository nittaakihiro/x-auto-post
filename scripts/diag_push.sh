#!/bin/bash
# CCRクラウド環境からのgit push経路診断（2026-07-11 障害調査用）
# 3経路を順に試し、成功した経路のcommit message / ファイル内容で判別する。
# 経路1: URL埋め込みトークンでgit push
# 経路2: Authorization: Basic ヘッダーでgit push
# 経路3: GitHub Contents API (curl相当のPUT)
# 失敗エラーはトークンをマスクして healthcheck.txt に記録する。
set -u
T="${DIAG_TOKEN:?DIAG_TOKEN env required — never hardcode tokens (public repo secret-scanning auto-revokes them)}"
TS=$(date -u +%Y%m%dT%H%M%SZ)
cd "$(dirname "$0")/.." || exit 1

echo "diag_${TS}" > healthcheck.txt
git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"
git add healthcheck.txt
git commit -m "healthcheck: diag ${TS}"

E1=$(git push "https://${T}@github.com/nittaakihiro/x-auto-post.git" HEAD:main 2>&1); R1=$?
if [ "$R1" -eq 0 ]; then
  echo "method1_url_token OK"
  exit 0
fi

B=$(printf 'x-access-token:%s' "$T" | base64 | tr -d '\n')
E2=$(git -c http.extraHeader="Authorization: Basic ${B}" push "https://github.com/nittaakihiro/x-auto-post.git" HEAD:main 2>&1); R2=$?
if [ "$R2" -eq 0 ]; then
  echo "method2_auth_header OK"
  exit 0
fi

E1="${E1//$T/TOKEN}"
E2="${E2//$T/TOKEN}"
export E1 E2 T TS
python3 - <<'PY'
import json, os, base64, urllib.request
t = os.environ['T']; ts = os.environ['TS']
body = "diag_%s\nmethod1_url_token FAIL:\n%s\nmethod2_auth_header FAIL:\n%s\nmethod3_contents_api: this commit\n" % (
    ts, os.environ['E1'], os.environ['E2'])
api = 'https://api.github.com/repos/nittaakihiro/x-auto-post/contents/healthcheck.txt'
req = urllib.request.Request(api, headers={'Authorization': 'token ' + t, 'User-Agent': 'diag'})
sha = json.load(urllib.request.urlopen(req))['sha']
data = json.dumps({'message': 'healthcheck: diag via contents-api ' + ts,
                   'content': base64.b64encode(body.encode()).decode(), 'sha': sha}).encode()
req = urllib.request.Request(api, data=data, method='PUT',
                             headers={'Authorization': 'token ' + t, 'User-Agent': 'diag',
                                      'Content-Type': 'application/json'})
print('API_PUT_STATUS', urllib.request.urlopen(req).status)
PY

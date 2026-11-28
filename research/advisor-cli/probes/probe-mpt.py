import http.server,threading,json,subprocess,os,time,tempfile,pathlib
from urllib.parse import urlparse
from collections import Counter
records=[]
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_POST(self):
  b=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
  mode=self.path.split("/")[1]
  records.append({"mode":mode,"path":self.path,"model":b.get("model"),"max_tokens":b.get("max_tokens"),"stream":b.get("stream")})
  code=200
  data={"id":"fixture","object":"chat.completion","created":1,"model":b.get("model"),"choices":[{"index":0,"message":{"role":"assistant","content":"synthetic-"+mode},"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"completion_tokens":3,"total_tokens":8}}
  if mode=="rate": code=429;data={"error":{"message":"synthetic rate limit","type":"rate_limit_error"}}
  if mode=="server": code=500;data={"error":{"message":"synthetic server error"}}
  if mode=="empty": data["choices"][0]["message"]["content"]=""
  if mode=="length": data["choices"][0]["finish_reason"]="length"
  if mode=="slow": time.sleep(2)
  raw=b"{bad" if mode=="bad" else json.dumps(data).encode()
  self.send_response(code);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(raw)))
  if code==429:self.send_header("Retry-After","10")
  self.end_headers()
  try:self.wfile.write(raw)
  except BrokenPipeError:pass
s=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler);threading.Thread(target=s.serve_forever,daemon=True).start()
p=pathlib.Path.cwd()
with tempfile.TemporaryDirectory() as home:
 env={"PATH":os.environ["PATH"],"HOME":home,"XDG_CONFIG_HOME":home,"LANG":"C.UTF-8"}
 outcomes=[]
 for modes in [("ok",),("ok","second"),("rate",),("server",),("bad",),("empty",),("length",),("slow",),("ok","rate")]:
  records.clear()
  cmd=[str(p/"mpt"),"--json","--timeout=1s","--retry.attempts=1","--prompt=Neutral synthetic probe"]
  for m in modes:cmd.extend(["--customs",f"{m}:url=http://127.0.0.1:{s.server_port}/{m}/v1,model=test-{m},max-tokens=64,enabled=true"])
  start=time.monotonic()
  try:
   r=subprocess.run(cmd,env=env,cwd=home,capture_output=True,text=True,timeout=6)
   row={"case":modes,"exit":r.returncode,"elapsed_ms":round((time.monotonic()-start)*1000),"requests":list(records),"stdout":r.stdout[:2000],"stderr":r.stderr[-1200:]}
  except subprocess.TimeoutExpired:row={"case":modes,"exit":"OUTER_TIMEOUT","requests":list(records)}
  outcomes.append(row);print(json.dumps(row,ensure_ascii=False))
 (p/"mpt-observations.json").write_text(json.dumps(outcomes,indent=2))
s.shutdown()

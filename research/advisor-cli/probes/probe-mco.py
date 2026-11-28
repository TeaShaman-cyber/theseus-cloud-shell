import os,sys,subprocess,json,time,pathlib,tempfile
d=pathlib.Path.cwd()
results=[]
for mode in ('ok','fail','slow','partial'):
 with tempfile.TemporaryDirectory() as home:
  w=pathlib.Path(home)/'witness.jsonl'
  env={'PATH':str(d/'mco-fake-bin')+':/usr/bin:/bin','HOME':home,'XDG_CONFIG_HOME':home,'LANG':'C.UTF-8','WITNESS':str(w),'FIXTURE_MODE':mode}
  cmd=[sys.executable,str(d/'mco-source/mco'),'review','--repo',str(d/'mco-fixture'),'--providers','claude,codex','--prompt','Synthetic read-only review','--execution-mode','read_only','--enforcement-mode','strict','--invocation-hard-timeout','2','--review-hard-timeout','5','--poll-interval','0.1','--include-token-usage','--json']
  start=time.monotonic()
  p=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=9)
  events=[json.loads(x) for x in w.read_text().splitlines()] if w.exists() else []
  live=[e['pid'] for e in events if pathlib.Path('/proc',str(e['pid'])).exists()]
  r={'case':mode,'exit':p.returncode,'elapsed_ms':round((time.monotonic()-start)*1000),'launches':events,'remaining_pids':live,'stdout':p.stdout,'stderr':p.stderr}
  results.append(r)
  print(json.dumps(r)[:4200])
(d/'mco-process-observations.json').write_text(json.dumps(results,indent=2))

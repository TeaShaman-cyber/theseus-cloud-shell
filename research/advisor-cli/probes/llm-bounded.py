import sys,json
from llm.default_plugins.openai_models import Chat
class BoundedChat(Chat):
 def get_client(self,key,*,async_=False):
  return super().get_client(key,async_=async_).with_options(max_retries=0,timeout=1.0)
m=BoundedChat(model_id=sys.argv[2],api_base=sys.argv[1])
m.needs_key=None
try:
 r=m.prompt("Neutral synthetic probe",stream=False,options={"max_tokens":64})
 text=r.text()
 raw=r.response_json
 finish=raw["choices"][0]["finish_reason"]
 print(json.dumps({"text":text,"finish":finish,"usage":raw.get("usage"),"model":raw.get("model")}))
 sys.exit(0 if text.strip() and finish=="stop" else 2)
except Exception as e:
 print(json.dumps({"error":type(e).__name__,"status":getattr(e,"status_code",None)}))
 sys.exit(1)

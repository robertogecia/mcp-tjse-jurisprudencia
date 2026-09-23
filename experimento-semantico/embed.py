import sqlite3,numpy as np,torch,time,os
from transformers import AutoTokenizer,AutoModel
M="intfloat/multilingual-e5-small"
tok=AutoTokenizer.from_pretrained(M);mod=AutoModel.from_pretrained(M).eval()
dev="mps" if torch.backends.mps.is_available() else "cpu";mod.to(dev)
con=sqlite3.connect(os.path.expanduser("~/.tjse-jurisprudencia/base/boletim.db"))
rows=con.execute("select acordao,ementa from acordaos order by acordao").fetchall()
ids=[r[0] for r in rows];txt=["passage: "+(r[1] or "")[:2000] for r in rows]
order=sorted(range(len(txt)),key=lambda i:len(txt[i]))
out=np.zeros((len(txt),384),dtype=np.float16);t=time.time()
with torch.no_grad():
  for k in range(0,len(order),64):
    b=order[k:k+64];e=tok([txt[i] for i in b],padding=True,truncation=True,max_length=320,return_tensors="pt").to(dev)
    h=mod(**e).last_hidden_state;m=e["attention_mask"].unsqueeze(-1)
    v=(h*m).sum(1)/m.sum(1);v=torch.nn.functional.normalize(v,dim=1)
    out[b]=v.float().cpu().numpy().astype(np.float16)
    if k%3200==0:print(k,round(time.time()-t),flush=True)
np.save("vetores.npy",out);open("ids.txt","w").write("\n".join(ids));print("ok",round(time.time()-t))

import sqlite3,numpy as np,json,os,re,sys,torch
from transformers import AutoTokenizer,AutoModel
M="intfloat/multilingual-e5-small"
tok=AutoTokenizer.from_pretrained(M);mod=AutoModel.from_pretrained(M).eval()
V=np.load("vetores.npy").astype(np.float32);ids=open("ids.txt").read().split("\n")
con=sqlite3.connect(os.path.expanduser("~/.tjse-jurisprudencia/base/boletim.db"))
def emb(q):
    e=tok(["query: "+q],return_tensors="pt",truncation=True,max_length=64)
    with torch.no_grad():h=mod(**e).last_hidden_state
    m=e["attention_mask"].unsqueeze(-1);v=(h*m).sum(1)/m.sum(1);return torch.nn.functional.normalize(v,dim=1)[0].numpy()
def fts(kw,n=10):
    t=" OR ".join('"%s"'%w for w in re.findall(r"\w+",kw))
    return [r[0] for r in con.execute("select a.acordao from fts f join acordaos a on a.rowid=f.rowid where fts match ? order by bm25(fts) limit ?",(t,n))]
def sem(q,n=10):
    s=V@emb(q);return [ids[i] for i in np.argsort(-s)[:n]]
def rrf(a,b,k=60,n=10):
    sc={}
    for l in(a,b):
        for r,x in enumerate(l):sc[x]=sc.get(x,0)+1/(k+r)
    return sorted(sc,key=lambda x:-sc[x])[:n]
Q=json.load(open("consultas.json"));out=[]
for nat,kw in Q:
    f=fts(kw,30);s=sem(nat,30);out.append({"q":nat,"kw":kw,"fts":f[:10],"sem":s[:10],"hib":rrf(f,s)})
json.dump(out,open("resultados.json","w"),ensure_ascii=False)
ac=sorted({x for o in out for k in("fts","sem","hib") for x in o[k]})
ement={a:(con.execute("select ementa from acordaos where acordao=?",(a,)).fetchone()[0] or "")[:260] for a in ac}
json.dump(ement,open("ementas.json","w"),ensure_ascii=False)
print(len(ac),"acórdãos a julgar")

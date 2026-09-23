import json,os,re,sqlite3,numpy as np,torch
from transformers import AutoTokenizer,AutoModelForSequenceClassification
import importlib.util
sp=importlib.util.spec_from_file_location("c","comparar.py")
# reaproveita funções sem reexecutar o laço: copia mínimo
from transformers import AutoModel
M="intfloat/multilingual-e5-small";tk=AutoTokenizer.from_pretrained(M);md=AutoModel.from_pretrained(M).eval()
V=np.load("vetores.npy").astype(np.float32);ids=open("ids.txt").read().split("\n")
con=sqlite3.connect(os.path.expanduser("~/.tjse-jurisprudencia/base/boletim.db"))
def emb(q):
    e=tk(["query: "+q],return_tensors="pt");
    with torch.no_grad():h=md(**e).last_hidden_state
    m=e["attention_mask"].unsqueeze(-1);v=(h*m).sum(1)/m.sum(1);return torch.nn.functional.normalize(v,dim=1)[0].numpy()
def fts(kw,n):
    t=" OR ".join('"%s"'%w for w in re.findall(r"\w+",kw))
    return [r[0] for r in con.execute("select a.acordao from fts f join acordaos a on a.rowid=f.rowid where fts match ? order by bm25(fts) limit ?",(t,n))]
R="BAAI/bge-reranker-v2-m3";rt=AutoTokenizer.from_pretrained(R);rm=AutoModelForSequenceClassification.from_pretrained(R).eval().to("mps")
def rerank(q,cands):
    tx=[(con.execute("select ementa from acordaos where acordao=?",(a,)).fetchone()[0] or "")[:1500] for a in cands];sc=[]
    with torch.no_grad():
        for i in range(0,len(cands),16):
            e=rt([q]*len(tx[i:i+16]),tx[i:i+16],padding=True,truncation=True,max_length=512,return_tensors="pt").to("mps")
            sc+=rm(**e).logits.view(-1).float().cpu().tolist()
    return [cands[i] for i in np.argsort(-np.array(sc))]
out=[]
for nat,kw in json.load(open("consultas.json")):
    f50=fts(kw,50);s=V@emb(nat);s30=[ids[i] for i in np.argsort(-s)[:30]]
    u=list(dict.fromkeys(f50[:30]+s30))
    out.append({"q":nat,"rrA":rerank(nat,f50)[:10],"rrB":rerank(nat,u)[:10]})
json.dump(out,open("resultados_rerank.json","w"),ensure_ascii=False);print("ok")

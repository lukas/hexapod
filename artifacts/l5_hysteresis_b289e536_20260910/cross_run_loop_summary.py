import csv, json, statistics

MID = -47.133
def load(p):
    out=[]
    for r in csv.DictReader(open(p)):
        try: out.append({"t":float(r["t_s"]),"c16":float(r["cmd16_deg"]),"q16":float(r["q16_deg"]),
                         "c17":float(r["cmd17_deg"]),"q17":float(r["q17_deg"]),
                         "cur16":float(r["cur16_a"] or 0),"load":float(r["load_pct"] or 0)})
        except (ValueError,KeyError): pass
    return out

def blocks(rows,min_s=2.0):
    res=[];i=0
    while i<len(rows):
        j=i
        while j+1<len(rows) and abs(rows[j+1]["c16"]-rows[i]["c16"])<1e-6: j+=1
        if rows[j]["t"]-rows[i]["t"]>=min_s:
            blk=rows[i:j+1]; tail=[r for r in blk if r["t"]>=rows[j]["t"]-1.0]
            res.append({"t0":rows[i]["t"],"t1":rows[j]["t"],"cmd16":rows[i]["c16"],
                        "q16":statistics.fmean(r["q16"] for r in tail),
                        "q17":statistics.fmean(r["q17"] for r in tail),
                        "cur16":max(r["cur16"] for r in blk),
                        "load":max(r["load"] for r in blk)})
        i=j+1
    return res

print(f"{'run':<34}{'hip loop (deg)':>17}{'knee loop':>11}{'sweep trk':>11}{'ramp trk':>10}{'pk A':>7}")
allw=[]
for p,l in [("attempt2.csv","THIS RUN 09-10T02:09:36Z"),
            ("prior_l5.csv","prior 09-06T00:54:45"),
            ("prior_20260905_222549.csv","prior 09-05T22:25:49"),
            ("prior_20260905_221555.csv","prior 09-05T22:15:55")]:
    rows=load(p); bs=blocks(rows)
    sw=[b for b in bs if b["cmd16"]<-40.0 and (b["t1"]-b["t0"])<5.0]
    for k,b in enumerate(sw):
        b["dir"]="out" if k and b["cmd16"]>sw[k-1]["cmd16"] else ("in" if k else "entry")
    mid=[b for b in sw if abs(b["cmd16"]-MID)<1e-3]
    o=[b for b in mid if b["dir"]=="out"]; n=[b for b in mid if b["dir"]=="in"]
    w=[(o[k]["q16"]-n[k]["q16"], o[k]["q17"]-n[k]["q17"]) for k in range(min(len(o),len(n)))]
    allw+= [x[0] for x in w]
    # sweep window = between end of entry settle and start of exit settle
    t_lo=min(b["t0"] for b in sw); t_hi=max(b["t1"] for b in sw)
    swept=[r for r in rows if t_lo<=r["t"]<=t_hi]
    trk_sw=max(max(abs(r["q16"]-r["c16"]),abs(r["q17"]-r["c17"])) for r in swept)
    trk_all=max(max(abs(r["q16"]-r["c16"]),abs(r["q17"]-r["c17"])) for r in rows)
    print(f"{l:<34}{statistics.fmean(x[0] for x in w):+9.3f}+-{statistics.pstdev([x[0] for x in w]):.3f}"
          f"{statistics.fmean(x[1] for x in w):+11.3f}{trk_sw:11.2f}{trk_all:10.2f}"
          f"{max(r['cur16'] for r in rows):7.3f}")
print(f"\npooled hip loop width across 4 runs (n={len(allw)} cycles): "
      f"mean {statistics.fmean(allw):+.3f} deg, sd {statistics.pstdev(allw):.3f}, "
      f"range {min(allw):+.3f}..{max(allw):+.3f}")
print("encoder resolution = 360/4096 = %.4f deg/count -> loop is %.1f counts"
      %(360/4096, abs(statistics.fmean(allw))/(360/4096)))
# direction-dependent sign check on this run
rows=load("attempt2.csv"); bs=blocks(rows)
sw=[b for b in bs if b["cmd16"]<-40.0 and (b["t1"]-b["t0"])<5.0]
for k,b in enumerate(sw):
    b["dir"]="out" if k and b["cmd16"]>sw[k-1]["cmd16"] else ("in" if k else "entry")
for d in ("out","in"):
    e=[b["q16"]-b["cmd16"] for b in sw if b["dir"]==d]
    c=[b["cur16"] for b in sw if b["dir"]==d]; L=[b["load"] for b in sw if b["dir"]==d]
    print(f"  {d:>3}-stroke settled hip error mean {statistics.fmean(e):+.3f} deg "
          f"(n={len(e)}), peak cur {max(c):.3f} A, peak load {max(L):.1f} %")

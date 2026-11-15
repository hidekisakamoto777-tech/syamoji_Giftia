import sys, json, re
src=open(sys.argv[1],encoding='utf-8').read()
cols=['product_id','product_name','category','price','brand','description','size','delivery_days','gift_wrap','message_card','rating','review_count','sales_count','stock','registered_at']
rows=[];cur=[];i=0;n=len(src)
while i<n:
    c=src[i]
    if c=="'":
        j=i+1;buf=[]
        while True:
            if src[j]=="\\": buf.append(src[j+1]); j+=2; continue
            if src[j]=="'":
                if j+1<n and src[j+1]=="'": buf.append("'"); j+=2; continue
                break
            buf.append(src[j]); j+=1
        cur.append(''.join(buf)); i=j+1
    elif c==',': i+=1
    elif c=='\n' or c=='\r':
        if cur: rows.append(cur); cur=[]
        i+=1
    else:
        m=re.match(r'[^,\n\r]+',src[i:]); tok=m.group(0); i+=len(tok)
        cur.append(None if tok=='NULL' else (float(tok) if '.' in tok else int(tok)))
if cur: rows.append(cur)
bad=[r for r in rows if len(r)!=len(cols)]
print("rows",len(rows),"bad",len(bad), bad[:1])
P=[dict(zip(cols,r)) for r in rows if len(r)==len(cols)]
for p in P:
    if p['rating'] is not None: p['rating']=float(p['rating'])
json.dump(P,open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False)

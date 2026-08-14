#!/usr/bin/env python3
"""Independently verify exact-edge mother CNFs and their complete cube cover."""

from __future__ import annotations

import argparse, hashlib, itertools, json
from pathlib import Path

from verify_order45_lex_benchmarks import independent_lex
from verify_order45_strengthened_benchmarks import edge_variable, expected_clauses

SCHEMA = "ramsey55.order45-edge-strata.v1"
RANGES = {20:(68,100),21:(77,107),22:(88,114),23:(101,122),24:(116,132)}
LIMIT = {20:226,21:222,22:220}


def counter(inputs, width, maximum):
    state, clauses = {}, []
    for i, item in enumerate(inputs, 1):
        for j in range(1, min(i, width) + 1):
            maximum += 1; current = state[i,j] = maximum
            if i == j == 1: clauses += [(-current,item),(-item,current)]
            elif j == 1:
                old=state[i-1,1]; clauses += [(-old,current),(-item,current),(-current,old,item)]
            elif j == i:
                diag=state[i-1,j-1]; clauses += [(-current,diag),(-current,item),(-diag,-item,current)]
            else:
                old,diag=state[i-1,j],state[i-1,j-1]
                clauses += [(-old,current),(-diag,-item,current),(-current,old,diag),(-current,old,item)]
    return maximum, clauses, tuple(state[len(inputs),j] for j in range(1,width+1))


def structure(degree):
    maximum=36190; cross=range(degree+1,45)
    rows=[tuple(edge_variable(a,b) for b in cross) for a in range(1,degree+1)]
    lex=[]
    for a,b in zip(rows,rows[1:]):
        maximum, part=independent_lex(a,b,maximum); lex += part
    h=tuple(edge_variable(u,v) for u,v in itertools.combinations(range(1,degree+1),2))
    j=tuple(-edge_variable(u,v) for u,v in itertools.combinations(range(degree+1,45),2))
    hmin,hmax=RANGES[degree]; jmin,jmax=RANGES[44-degree]
    maximum,hclauses,hout=counter(h,hmax+1,maximum)
    maximum,jclauses,jout=counter(j,jmax+1,maximum)
    bounds=[(hout[hmin-1],),(-hout[hmax],),(jout[jmin-1],),(-jout[jmax],)]
    sums=[]
    for k in range(LIMIT[degree]):
        clause=[]
        for required,out in ((k+1,hout),(LIMIT[degree]-k,jout)):
            if required <= len(out): clause.append(out[required-1])
        if clause: sums.append(tuple(clause))
        else: sums.append(())
    cubes=[{"edges_h":x,"edges_j":y,
            "literals":[hout[x-1],-hout[x],jout[y-1],-jout[y]]}
           for x in range(hmin,hmax+1) for y in range(jmin,jmax+1)
           if x+y >= LIMIT[degree]]
    return maximum, lex, hclauses, jclauses, bounds, sums, cubes


def expected(degree):
    yield from expected_clauses(degree)
    _,lex,h,j,bounds,sums,_=structure(degree)
    yield from lex; yield from h; yield from j; yield from bounds; yield from sums


def sha(path):
    d=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""): d.update(block)
    return d.hexdigest()


def main():
    p=argparse.ArgumentParser(); p.add_argument("manifest",type=Path); p.add_argument("--cnf-dir",type=Path)
    a=p.parse_args(); doc=json.loads(a.manifest.read_text())
    if doc.get("schema") != SCHEMA: raise ValueError("bad schema")
    root=a.cnf_dir or a.manifest.parent
    for record in doc["files"]:
        degree=record["degree"]; maximum,*_,cubes=structure(degree)
        if maximum != record["variables"] or cubes != record["cubes"]:
            raise ValueError(f"d{degree}: variable map or cube cover differs")
        path=root/record["path"]
        with path.open() as f:
            if f.readline().split() != ["p","cnf",str(maximum),str(record["clauses"])]: raise ValueError("bad header")
            count=0
            for count,clause in enumerate(expected(degree),1):
                fields=f.readline().split()
                if not fields or fields[-1]!="0" or tuple(map(int,fields[:-1]))!=clause: raise ValueError(f"d{degree}: clause {count}")
            if count!=record["clauses"] or f.readline(): raise ValueError("bad count")
        if sha(path)!=record["sha256"]: raise ValueError("bad hash")
        print(f"verified d{degree}: {count} clauses, {len(cubes)} disjoint covering cubes")

if __name__ == "__main__": main()

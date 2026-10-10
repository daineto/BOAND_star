"""Exhaustive small-grid FrozenLake oracle, independent of BOAND search.

Enumerates stationary policies, including cyclic policies, using the unchanged
ice/wall/pit movement rules. Only suitable for small exploratory instances.
"""
import argparse
import itertools
import json
from collections import deque
from pathlib import Path

def evaluate(graph,start,goal):
    dist={start:0};queue=deque([start]);edges={}
    while queue:
        s=queue.popleft();edges[s]=[] if s==goal else graph[s]
        for t in edges[s]:
            if t not in dist:dist[t]=dist[s]+1;queue.append(t)
    if goal not in dist:return None
    rev={s:[] for s in dist};degree={s:0 for s in dist}
    for s,ts in edges.items():
        for t in ts:rev[t].append(s);degree[t]+=1
    seen={goal};queue=deque([goal])
    while queue:
        for s in rev[queue.popleft()]:
            if s not in seen:seen.add(s);queue.append(s)
    if len(seen)!=len(dist):return None
    queue=deque(s for s in dist if degree[s]==0);longest={s:0 for s in dist};n=0
    while queue:
        s=queue.popleft();n+=1
        for t in edges[s]:
            longest[t]=max(longest[t],longest[s]+1);degree[t]-=1
            if degree[t]==0:queue.append(t)
    return dist[goal],longest[goal] if n==len(dist) else float('inf')

def frontier(cells,start,goal,max_policies=200000):
    actions={}
    for s,kind in cells.items():
        if kind!='ice' or s==goal:continue
        opts=[]
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            t=(s[0]+dx,s[1]+dy);u=(s[0]+2*dx,s[1]+2*dy)
            if cells.get(t,'wall')!='ice':continue
            k=cells.get(u,'wall')
            if k=='pit':continue
            opts.append((t,) if k=='wall' else (t,u))
        # A dead-end state has no valid policy assignment. A self-loop is an
        # enumeration placeholder: it is rejected whenever reachable.
        actions[s]=opts or [(s,)]
    keys=list(actions);count=1
    for k in keys:count*=len(actions[k])
    if count>max_policies:raise ValueError(f'Grid requires {count} policies; exhaustive limit is {max_policies}')
    costs=set()
    for choices in itertools.product(*(actions[k] for k in keys)):
        pair=evaluate(dict(zip(keys,choices)),start,goal)
        if pair:costs.add(pair)
    front=sorted(p for p in costs if not any(q!=p and q[0]<=p[0] and q[1]<=p[1] for q in costs))
    return front,count

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grids", type=Path)
    parser.add_argument("--max-policies", type=int, default=200000)
    args = parser.parse_args()
    records = json.loads(args.grids.read_text())["instances"]
    results = []
    for number, record in enumerate(records, 1):
        cells = {(x, y): kind for x, y, kind in record["cells"]}
        front, count = frontier(cells, tuple(record["start"]), tuple(record["goal"]), args.max_policies)
        actual = [[b, 999999 if w == float('inf') else w] for b, w in front]
        if actual != record["front"]:
            raise ValueError(f"Instance {number}: {actual} != {record['front']}")
        results.append({"instance": record.get('instance', f"tradeoff-{number:02d}"), "front": actual,
                        "policies_enumerated": count})
    print(json.dumps(results, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

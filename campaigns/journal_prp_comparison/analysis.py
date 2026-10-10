"""First valid policy timing and bi-objective quality; never average infinity."""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import statistics
from analysis.comparison_support import selected_results,cost_set,search_complete
from experiment_support.campaigns import read_instances,resolve_dataset
from experiment_support.configurations import PAPER_CONFIGURATIONS
from campaigns.icaps2025.campaign import CAMPAIGN as HISTORICAL
from campaigns.journal_icaps_comparison.campaign import CAMPAIGN as NATIVE
from planner.policy import CYCLE_COST
from .campaign import CAMPAIGN

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_OLD=ROOT/'runs/icaps2025/2026-10-07T14-01-07Z-BOAND_bw-c6171249'
DEFAULT_NATIVE=ROOT/'runs/journal_icaps_comparison/2026-10-09T12-43-05Z-paper-05dc1b6e'


def costs(pair):return tuple(math.inf if x==CYCLE_COST else x for x in pair)
def dominates(a,b):return all(x<=y for x,y in zip(costs(a),costs(b))) and any(x<y for x,y in zip(costs(a),costs(b)))
def relation(prp,front):
    if tuple(prp) in {tuple(x) for x in front}:return 'on_front'
    if any(dominates(x,prp) for x in front):return 'dominated_by_boand'
    if any(dominates(prp,x) for x in front):return 'dominates_boand_point'
    return 'incomparable'
def gm(values):return math.exp(statistics.mean(map(math.log,values))) if values else None


def compare(prp_path,native_path=DEFAULT_NATIVE,old_path=DEFAULT_OLD,output=None):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    prp_path=Path(prp_path).resolve();output=Path(output or prp_path/'comparison').resolve();output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((prp_path/'manifest.json').read_text())
    if json.loads((prp_path/'status.json').read_text()).get('state')!='finished':raise ValueError('PRP campaign execution/replay is not finished')
    entries=read_instances(CAMPAIGN,manifest['profile']);ids={(e['domain'],e['instance']) for e in entries}
    native,errors=selected_results(resolve_dataset(NATIVE,native_path)[0],NATIVE.configurations,ids)
    old,old_errors=selected_results(resolve_dataset(HISTORICAL,old_path)[0],{'Pyperplan hmax':PAPER_CONFIGURATIONS['BOAND bw']},ids)
    if errors or old_errors:raise ValueError(f'Malformed BOAND stats: {errors}, {old_errors}')
    checks=json.loads((Path(native_path)/'comparison/policy-validation.json').read_text())
    rows=[];prp_rows={};quality=[]
    for entry in entries:
        domain,instance=entry['domain'],entry['instance'];folder=prp_path/domain/instance
        execution=json.loads((folder/'execution.json').read_text());validation=json.loads((folder/'validation.json').read_text())
        valid=validation['status']=='valid';timed=execution.get('first_policy_search_seconds')
        row={'configuration':'PRP','domain':domain,'instance':instance,'has_policy':(folder/'policy.out').exists(),
             'validated':valid,'validation_status':validation['status'],'termination':execution['termination'],
             'first_seconds':timed if valid else None,'first_wall_seconds':execution.get('policy_available_wall_seconds') if valid else None,
             'best':validation.get('best') if valid else None,'worst':validation.get('worst') if valid else None,
             'peak_planner_rss_kb':execution.get('peak_child_rss_kb'),'reachable_states':validation.get('reachable_states'),
             'policy_rules':validation.get('policy_rules'),'replay_error':validation.get('error')}
        rows.append(row);prp_rows[domain,instance]=row
    for label,runs in [*( (label,native) for label in NATIVE.configurations),('Pyperplan hmax',old)]:
        for domain,instance in sorted(ids):
            run=runs[label,domain,instance];first=run.first_solution;legacy=label=='Pyperplan hmax'
            check=checks.get('/'.join((label,domain,instance)),{})
            supplemental=(label,domain,instance)==('FD hmax','beam-walk','p11') and (ROOT/'outputs/full-review/findings.json').exists()
            verified=legacy or check.get('status')=='valid' or supplemental
            row={'configuration':label,'domain':domain,'instance':instance,'has_policy':bool(first),'validated':bool(first) and verified,
                 'validation_status':'legacy_unchecked' if legacy else 'valid_supplemental' if supplemental else check.get('status'),
                 'termination':(run.execution or {}).get('termination'),'first_seconds':first['time'] if first and verified else None,
                 'best':first['best'] if first and verified else None,'worst':first['worst'] if first and verified else None}
            rows.append(row)
            prp=prp_rows[domain,instance]
            if not legacy and first and verified and prp['validated']:
                front=cost_set(run);completed=search_complete(run)
                q={'configuration':label,'domain':domain,'instance':instance,'prp_best':prp['best'],'prp_worst':prp['worst'],
                   'boand_first_best':first['best'],'boand_first_worst':first['worst'],
                   'boand_completed':completed,'front':front,
                   'first_relation':relation((prp['best'],prp['worst']),[(first['best'],first['worst'])]),
                   'front_relation':relation((prp['best'],prp['worst']),front) if completed else 'incomplete_front',
                   'min_front_best':min(x[0] for x in front) if completed else None,
                   'min_front_worst':min(x[1] for x in front) if completed else None}
                quality.append(q)
    counts={label:{'with_policy':sum(r['has_policy'] for r in rows if r['configuration']==label),
                   'validated_or_legacy_reported':sum(r['validated'] for r in rows if r['configuration']==label),
                   'timed_coverage':sum(r['first_seconds'] is not None for r in rows if r['configuration']==label)}
            for label in ('Pyperplan hmax','FD hmax','FD lmcut','PRP')}
    summary={}
    for label in NATIVE.configurations:
        paired=[q for q in quality if q['configuration']==label];complete=[q for q in paired if q['boand_completed']]
        ratios=[q['prp_best']/q['boand_first_best'] for q in paired if q['prp_best']>0 and q['boand_first_best']>0]
        finiteworst=[q for q in paired if q['prp_worst']!=CYCLE_COST and q['boand_first_worst']!=CYCLE_COST]
        wratios=[q['prp_worst']/q['boand_first_worst'] for q in finiteworst if q['prp_worst']>0 and q['boand_first_worst']>0]
        summary[label]={'paired_valid_policies':len(paired),'first_solution_relations':dict(Counter(q['first_relation'] for q in paired)),
                        'completed_front_pairs':len(complete),'completed_front_relations':dict(Counter(q['front_relation'] for q in complete)),
                        'prp_to_boand_first_best_geomean_ratio':gm(ratios),'positive_best_ratio_pairs':len(ratios),
                        'both_finite_worst_pairs':len(finiteworst),'positive_finite_worst_ratio_pairs':len(wratios),
                        'prp_to_boand_first_finite_worst_geomean_ratio':gm(wratios),
                        'prp_cyclic_boand_first_finite':sum(q['prp_worst']==CYCLE_COST and q['boand_first_worst']!=CYCLE_COST for q in paired),
                        'prp_finite_boand_first_cyclic':sum(q['prp_worst']!=CYCLE_COST and q['boand_first_worst']==CYCLE_COST for q in paired),
                        'both_cyclic':sum(q['prp_worst']==CYCLE_COST and q['boand_first_worst']==CYCLE_COST for q in paired)}
        timing=[(next(r['first_seconds'] for r in rows if r['configuration']==label and (r['domain'],r['instance'])==(q['domain'],q['instance'])),prp_rows[q['domain'],q['instance']]['first_seconds']) for q in paired]
        ratios_t=[a/b for a,b in timing if a is not None and b is not None and a>0 and b>0]
        summary[label]['boand_to_prp_first_search_time_geomean_ratio']=gm(ratios_t)
        summary[label]['positive_first_time_pairs']=len(ratios_t)
    resources=json.loads((prp_path/'resources.json').read_text());issues=[r for r in rows if r['configuration']=='PRP' and r['has_policy'] and not r['validated']]
    report={'campaign':CAMPAIGN.campaign_id,'version':CAMPAIGN.version,'counts':counts,'quality':summary,
            'prp_terminations':dict(Counter(r['termination'] for r in prp_rows.values())),
            'prp_validation_status':dict(Counter(r['validation_status'] for r in prp_rows.values())),
            'validation_issues':issues,'resource_summary':{'min_available_gib':min(r['available_kb'] for r in resources)/1048576,
            'max_swap_mib':max(r['swap_used_kb'] for r in resources)/1024,'max_concurrent_jobs':max(r['active_jobs'] for r in resources)},
            'limitations':['Single run per case, no timing variability estimate.',
                'PRP time is wall time from search-stage launch to post-construction simulation marker; trials=0 removes post-planning simulation. It bounds time to its first final closed policy, not initial all-outcome classical plan.',
                'BOAND first-solution time is internal elapsed search time; neither search-axis timer includes translation/grounding. PRP launch overhead remains; extra end-to-end CSV timings include it.',
                'Legacy Pyperplan policies are reported, not revalidated. Its resources were 8 GB/two workers versus current 6 GB/four.',
                'Original-PDDL replay checks exported priority and forbidden-action rules, applicability, all outcomes, goal reachability, shortest best and cyclic/longest worst. It does not prove Pareto completeness.',
                'Cycle sentinel 999999 is infinity, excluded from finite cost ratios. Best and worst component minima may belong to different BOAND policies.',
                'BOAND optimal-front comparisons use only completed searches; timeout incumbents are first-solution comparisons only.']}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    for name,data in [('instances.csv',rows),('quality.csv',quality)]:
        if not data:continue
        with (output/name).open('w',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=sorted(set().union(*(r.keys() for r in data))));writer.writeheader();writer.writerows(data)
    styles=[('Pyperplan hmax','#666666','--'),('FD hmax','#0072B2','-'),('FD lmcut','#D55E00','-'),('PRP','#009E73','-')]
    fig,ax=plt.subplots(figsize=(7,4.5))
    for label,color,style in styles:
        times=sorted(max(1e-6,r['first_seconds']) for r in rows if r['configuration']==label and r['first_seconds'] is not None and r['first_seconds']<=600)
        ax.step([1e-6,*times,600],[0,*range(1,len(times)+1),len(times)],where='post',color=color,ls=style,label=f'{label.replace("lmcut","LM-cut")}{", reported" if label=="Pyperplan hmax" else ""} ({len(times)})',lw=1.8)
    ax.set(xscale='log',xlim=(1e-4,600),ylim=(0,len(entries)),xlabel='Time to first policy during search (s)',ylabel='Instances with a policy');ax.legend(loc='lower right');ax.grid(alpha=.3);fig.tight_layout()
    for ext in ('pdf','svg','png'):fig.savefig(output/f'first-solution-coverage.{ext}',dpi=200)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for ax,label in zip(axes,NATIVE.configurations):
        pairs=[q for q in quality if q['configuration']==label and q['prp_best']>0 and q['boand_first_best']>0]
        ax.scatter([q['boand_first_best'] for q in pairs],[q['prp_best'] for q in pairs],s=20,alpha=.7,color='#009E73')
        highest=max([q['prp_best'] for q in pairs]+[q['boand_first_best'] for q in pairs]+[1]);ax.plot([1,highest],[1,highest],'k--',lw=.8)
        ax.set(xscale='log',yscale='log',xlabel=f'{label} first-policy best cost',ylabel='PRP best cost',title='Below diagonal: PRP lower best cost');ax.grid(alpha=.2)
    fig.tight_layout()
    for ext in ('pdf','svg','png'):fig.savefig(output/f'best-cost-comparison.{ext}',dpi=200)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4.2))
    categories=['on_front','dominated_by_boand','incomparable','dominates_boand_point']
    for ax,label in zip(axes,NATIVE.configurations):
        counts_q=summary[label]['completed_front_relations'];values=[counts_q.get(c,0) for c in categories]
        ax.bar(range(4),values,color=['#009E73','#D55E00','#0072B2','#CC79A7'])
        ax.set_xticks(range(4),['Matches front','BOAND dominates','Tradeoff','PRP dominates'],rotation=30,ha='right')
        ax.set(title=label,ylabel='Instances with both valid policies and completed BOAND front')
        for x,value in enumerate(values):ax.text(x,value+.2,str(value),ha='center')
    fig.tight_layout()
    for ext in ('pdf','svg','png'):fig.savefig(output/f'frontier-quality.{ext}',dpi=200)
    plt.close(fig)
    lines=['# PRP versus BOAND*: first policy and quality','',f'PRP run: `{prp_path}`','', '| Planner | Policies | Validated/reported | Timed coverage |','| --- | ---: | ---: | ---: |']
    for label,c in counts.items():lines.append(f"| {label} | {c['with_policy']} | {c['validated_or_legacy_reported']} | {c['timed_coverage']} |")
    lines+=['','## Solution quality','','Comparison with completed BOAND fronts; cyclic worst cost is infinity.','',
            '| BOAND reference | Paired first policies | Completed fronts | PRP on front | BOAND dominates PRP | Incomparable | PRP dominates a front point |',
            '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for label,q in summary.items():
        relations=q['completed_front_relations'];lines.append(f"| {label} | {q['paired_valid_policies']} | {q['completed_front_pairs']} | {relations.get('on_front',0)} | {relations.get('dominated_by_boand',0)} | {relations.get('incomparable',0)} | {relations.get('dominates_boand_point',0)} |")
    lines+=['','Detailed first-policy cost and time ratios are in report.json; per-instance frontiers are in quality.csv.',
            'The first-time ratio is BOAND/PRP: greater than one means PRP was faster. It compares different output guarantees and potentially different policy quality.',
            '',f"PRP termination counts: {report['prp_terminations']}",f"Replay outcomes: {report['prp_validation_status']}",'','## Limitations','',*('- '+x for x in report['limitations'])]
    (output/'report.md').write_text('\n'.join(lines)+'\n');print(json.dumps(report,indent=2));return report


def main():
    p=argparse.ArgumentParser();p.add_argument('prp_run',type=Path);p.add_argument('--native',type=Path,default=DEFAULT_NATIVE);p.add_argument('--old',type=Path,default=DEFAULT_OLD);p.add_argument('--output',type=Path);args=p.parse_args();compare(args.prp_run,args.native,args.old,args.output)

if __name__=='__main__':main()

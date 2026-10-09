"""Version-1 comparison rules for current native runs and the published archive."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics

from analysis.comparison_support import cost_set, elapsed_time, replay_runs, search_complete, selected_results
from campaigns.icaps2025.campaign import CAMPAIGN as HISTORICAL, PAPER_CONFIGURATIONS
from experiment_support.campaigns import input_path, read_instances, resolve_dataset
from .campaign import CAMPAIGN, DOMAINS

HISTORY = 'Historical BOAND bw'


def compare(directory, output=None, replay=True):
    directory = Path(directory).resolve()
    manifest = json.loads((directory/'manifest.json').read_text())
    root, identity = resolve_dataset(CAMPAIGN, directory)
    entries = read_instances(CAMPAIGN, manifest['profile'])
    ids = {(e['domain'], e['instance']) for e in entries}
    inputs = {(e['domain'], e['instance']): {**e, 'domain_path': str(input_path(e['domain_path'])),
                                             'problem_path': str(input_path(e['problem_path']))} for e in entries}
    current, parse_errors = selected_results(root, CAMPAIGN.configurations, ids)
    expected_keys = {(label, *key) for label in CAMPAIGN.configurations for key in ids}
    if set(current) != expected_keys:
        raise ValueError('Result identities do not match the selected campaign')
    output = Path(output or directory/'comparison').resolve(); output.mkdir(parents=True, exist_ok=True)
    validation = replay_runs(current, inputs, output/'policy-replay') if replay else {
        key: {'status': 'not_checked'} for key in current}
    (output/'policy-validation.json').write_text(json.dumps({'/'.join(k): v for k,v in validation.items()},indent=2)+'\n')
    historical, historical_errors = selected_results(HISTORICAL.archive_root, {HISTORY: PAPER_CONFIGURATIONS['BOAND bw']}, ids)
    telemetry = json.loads((directory/'resources.json').read_text()) if (directory/'resources.json').exists() else {}
    rows=[]; indexed={}
    for label in (*CAMPAIGN.configurations, HISTORY):
        for domain,instance in sorted(ids):
            key=(label,domain,instance); run=(historical if label==HISTORY else current).get(key)
            old=label==HISTORY
            check={'status':'historical_unchecked'} if old else validation[key]
            complete=bool(run and search_complete(run,historical=old))
            costs=cost_set(run) if run else []
            execution=(run.execution or {}) if run else {}
            verified=check['status'] in ('valid','no_policies')
            row={'configuration':label,'domain':domain,'instance':instance,
                 'search_complete':complete,'validated_complete':complete and verified,
                 'has_incumbent':bool(costs),'verified_solved':bool(costs) and check['status']=='valid',
                 'policy_validation':check['status'],'execution_state':execution.get('state'),
                 'returncode':execution.get('returncode'),'termination':execution.get('termination'),
                 'search_seconds':run.stats[-1]['time'] if complete else None,
                 'first_solution_seconds':run.first_solution['time'] if run and run.first_solution else None,
                 'job_wall_seconds':elapsed_time(run) if run and not old else None,
                 'sampled_peak_rss_kb':telemetry.get('planner_peaks_kb',{}).get(f"{CAMPAIGN.configurations[label].classical}/{domain}/{instance}") if not old else None,
                 'expansions':run.stats[-1]['expansions'] if complete else None,
                 'generations':run.stats[-1]['generations'] if complete else None,
                 'costs':costs,'source':str(run.directory) if run else None}
            rows.append(row);indexed[key]=row
    # The smoke profile has a correctness oracle in addition to independent replay.
    failures=[{'case':'/'.join(k),'error':v} for k,v in parse_errors.items()]
    for key,run in current.items():
        execution=run.execution or {}
        if execution.get('state')!='finished' or execution.get('returncode') not in (0,124):
            failures.append({'case':'/'.join(key),'error':'Execution failure','execution':execution})
        elif execution.get('returncode')==0 and not run.complete:
            failures.append({'case':'/'.join(key),'error':'Successful execution without completion marker'})
    if manifest['profile']=='smoke':
        expected=json.loads(Path(__file__).with_name('smoke-expected.json').read_text())['costs']
        for key,row in indexed.items():
            if key[0]==HISTORY:continue
            if not row['validated_complete'] or [list(c) for c in row['costs']]!=expected['/'.join(key[1:])]:
                failures.append({'case':'/'.join(key),'error':'Smoke coverage, replay or cost mismatch'})
    else:
        for key,check in validation.items():
            if check['status'] not in ('valid','no_policies'):
                failures.append({'case':'/'.join(key),**check})
    disagreements=[];historical_differences=[];pairs=[]
    for domain,instance in sorted(ids):
        a,b=(indexed[label,domain,instance] for label in CAMPAIGN.configurations)
        if a['validated_complete'] and b['validated_complete'] and a['costs']!=b['costs']:
            disagreements.append({'domain':domain,'instance':instance,'hmax_costs':a['costs'],'lmcut_costs':b['costs']})
        old=indexed[HISTORY,domain,instance]
        for label in CAMPAIGN.configurations:
            new=indexed[label,domain,instance]
            same=old['costs']==new['costs']
            if old['search_complete'] and new['validated_complete'] and not same:
                historical_differences.append({'configuration':label,'domain':domain,'instance':instance,
                                               'historical_costs':old['costs'],'current_costs':new['costs']})
            if old['search_complete'] and new['validated_complete'] and same and old['search_seconds']>0 and new['search_seconds']>0:
                pairs.append({'configuration':label,'domain':domain,'instance':instance,
                              'historical_seconds':old['search_seconds'],'current_seconds':new['search_seconds'],
                              'speedup':old['search_seconds']/new['search_seconds']})
    counts={}
    for label in (*CAMPAIGN.configurations,HISTORY):
        selected=[r for r in rows if r['configuration']==label]
        counts[label]={'instances':len(selected),'completed_searches':sum(r['search_complete'] for r in selected),
                       'validated_complete':sum(r['validated_complete'] for r in selected),
                       'with_incumbent':sum(r['has_incumbent'] for r in selected),
                       'verified_solved':sum(r['verified_solved'] for r in selected),
                       'timeouts':sum(r['termination']=='timeout' for r in selected),
                       'execution_failures':sum(r['returncode'] not in (0,124,None) for r in selected)}
    native_pairs=[]
    for domain,instance in sorted(ids):
        a,b=(indexed[label,domain,instance] for label in CAMPAIGN.configurations)
        if a['validated_complete'] and b['validated_complete'] and a['costs']==b['costs'] and a['search_seconds']>0 and b['search_seconds']>0:
            native_pairs.append({'domain':domain,'instance':instance,'hmax_seconds':a['search_seconds'],
                                 'lmcut_seconds':b['search_seconds'],'lmcut_speedup':a['search_seconds']/b['search_seconds']})
    counts[HISTORY].update(validated_complete=None,verified_solved=None,timeouts=None,execution_failures=None)
    timing={}
    for label in CAMPAIGN.configurations:
        values=[p['speedup'] for p in pairs if p['configuration']==label]
        timing[label]={'paired_completed_equal_cost_instances':len(values),
                       'historical_search_geomean_speedup':math.exp(statistics.mean(map(math.log,values))) if values else None}
    report={'campaign':CAMPAIGN.campaign_id,'version':CAMPAIGN.version,'dataset':identity,
            'status':'needs_investigation' if failures or disagreements else 'historical_differences_to_review' if historical_differences else 'checked',
            'counts':counts,'historical_timing':timing,
            'native_timing':{'paired_completed_equal_cost_instances':len(native_pairs),
                             'lmcut_geomean_search_speedup_over_hmax':math.exp(statistics.mean(math.log(p['lmcut_speedup']) for p in native_pairs)) if native_pairs else None},'validation_issues':failures,
            'historical_parse_issues':{'/'.join(k):v for k,v in historical_errors.items()},
            'native_cost_disagreements':disagreements,'historical_cost_differences':historical_differences,
            'limitations':['One measurement per case; no timing variability estimate.',
              'Historical runs used 8,000,000 KB/two workers, current runs use 6,000,000 KB/four workers.',
              'Historical machine/load and original search semantics differ; speedups do not isolate migration.',
              'Historical policies are not revalidated; costs may reflect corrected legacy bugs.',
              'Policy replay uses independent Python transitions/reference preprocessing and graph-cost checks; it does not prove Pareto completeness or unsolvability.',
              'Replay is bounded to 600 seconds and 6,000,000 KB per instance; unresolved replay is reported.',
              'Sampled memory can miss short processes or exit-time peaks; historical memory is unavailable.',
              'Plots floor zero times at one microsecond; raw timings are preserved and zero-time pairs are excluded from speedups.',
              'Configurations execute in recorded scheduler order, not randomized paired repetitions.']}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    for name,items in [('instances.csv',rows),('historical-timing-pairs.csv',pairs),('native-timing-pairs.csv',native_pairs)]:
        if not items:continue
        with (output/name).open('w') as file:
            writer=csv.DictWriter(file,fieldnames=list(items[0]));writer.writeheader();writer.writerows(items)
    lines=['# Full ICAPS input comparison','',f"Status: **{report['status']}**.",'',
           '| Configuration | Completed searches | With incumbent | Verified solved | Timeouts |',
           '| --- | ---: | ---: | ---: | ---: |']
    for label,c in counts.items():lines.append(f"| {label} | {c['completed_searches']} | {c['with_incumbent']} | {c['verified_solved'] if label!=HISTORY else 'not checked'} | {c['timeouts'] if label!=HISTORY else 'unknown'} |")
    domain_counts=[]
    for domain in DOMAINS:
        for label in counts:
            items=[r for r in rows if r['domain']==domain and r['configuration']==label]
            if not items:continue
            domain_counts.append({'domain':domain,'configuration':label,'selected':len(items),
                                  'completed':sum(r['search_complete'] for r in items),
                                  'with_incumbent':sum(r['has_incumbent'] for r in items),
                                  'verified_solved':sum(r['verified_solved'] for r in items)})
    with (output/'domain-counts.csv').open('w') as file:
        writer=csv.DictWriter(file,fieldnames=list(domain_counts[0]));writer.writeheader();writer.writerows(domain_counts)
    lines+=['',f"Native completed-cost disagreements: {len(disagreements)}. Historical completed-cost differences: {len(historical_differences)}.",'',*['- '+s for s in report['limitations']]]
    (output/'report.md').write_text('\n'.join(lines)+'\n')
    plots(rows,pairs,output)
    print(json.dumps({'output':str(output),'status':report['status'],'counts':counts},indent=2),flush=True)
    return report


def plots(rows,pairs,output):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    fig,ax=plt.subplots()
    for label in (*CAMPAIGN.configurations,HISTORY):
        times=sorted(max(1e-6,r['search_seconds']) for r in rows if r['configuration']==label and
                     (r['search_complete'] if label==HISTORY else r['validated_complete']))
        ax.step(times,range(1,len(times)+1),where='post',label=label)
    ax.set(xlabel='Search time (s)',ylabel='Completed searches',xscale='log');ax.legend();fig.tight_layout()
    fig.savefig(output/'completion-cactus.pdf');plt.close(fig)
    fig,ax=plt.subplots()
    for label in (*CAMPAIGN.configurations,HISTORY):
        times=sorted(max(1e-6,r['first_solution_seconds']) for r in rows if r['configuration']==label and
                     (r['has_incumbent'] if label==HISTORY else r['verified_solved']))
        ax.step(times,range(1,len(times)+1),where='post',label=label)
    ax.set(xlabel='Time to first policy (s)',ylabel='Instances with a policy',xscale='log');ax.legend();fig.tight_layout()
    fig.savefig(output/'solution-cactus.pdf');plt.close(fig)
    fig,ax=plt.subplots()
    for label in CAMPAIGN.configurations:
        selected=[p for p in pairs if p['configuration']==label]
        ax.scatter([p['historical_seconds'] for p in selected],[p['current_seconds'] for p in selected],label=label,s=15,alpha=.7)
    ax.plot([1e-6,600],[1e-6,600],color='grey',linestyle='--')
    ax.set(xscale='log',yscale='log',xlabel='Historical search time (s)',ylabel='Current search time (s)');ax.legend();fig.tight_layout()
    fig.savefig(output/'historical-search-scatter.pdf');plt.close(fig)


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--dataset',required=True,type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv);compare(args.dataset,args.output)


if __name__=='__main__':main()

"""Generate retrospective figures from preserved optimization measurements."""
import csv
import json
import re
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'outputs/performance-report'


def read(path):
    return json.loads((ROOT / path).read_text())


def generate():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.backends.backend_pdf import PdfPages
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for round_number in range(1, 13):
        folder = Path(f'outputs/performance/round{round_number}')
        for row in read(folder / 'round-summary.json'):
            label = str(row.get('attempt', row.get('label')))
            match = re.fullmatch(r'(?:attempt)?(\d+)', label)
            if label == 'baseline':
                number = 0
            elif match:
                number = int(match[1])
            else:
                # Refinements remain in the exported table, separately labelled.
                number = None
            detail_path = ROOT / folder / (f'attempt{number}' if number else label) / 'summary.json'
            detail = json.loads(detail_path.read_text()) if detail_path.exists() else {}
            bounds = detail.get('suite_wall_range', [row.get('suite_wall_min'), row.get('suite_wall_max')])
            low, high = bounds
            median = row['suite_wall_median']
            if low is not None and not low <= median <= high:
                # Summaries can use extended repetitions while detail preserves
                # the initial evaluation. Never mix incompatible uncertainty.
                low = high = None
            rows.append({'attempt': number, 'label': label, 'round': round_number,
                         'profile': 'smoke' if round_number <= 8 else 'performance',
                         'decision': row['decision'], 'revision': row.get('revision'),
                         'repeats': row.get('repeats', row.get('repetitions')),
                         'suite_median': median, 'suite_min': low, 'suite_max': high,
                         'parent_speedup': row.get('parent_speedup', row.get('search_speedup_parent', row.get('speedup'))),
                         'ci_low': row.get('parent_ci_low', row.get('ci_low')),
                         'ci_high': row.get('parent_ci_high', row.get('ci_high')),
                         'source': str(folder / 'round-summary.json')})
    with (OUTPUT / 'attempts.csv').open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
    figures = []
    def save(fig, name):
        fig.tight_layout()
        for extension in ('png','pdf','svg'):
            fig.savefig(OUTPUT / f'{name}.{extension}', dpi=180)
        figures.append(fig)
    colors = {'keep':'#0072B2','revert':'#D55E00','cleanup':'#009E73','reference':'#555555'}
    def category(row):
        if row['attempt'] == 34: return 'revert'
        decision = row['decision']
        return 'cleanup' if 'cleanup' in decision or 'memory' in decision else 'keep' if decision == 'keep' else 'reference' if decision == 'reference' else 'revert'
    fig, axes = plt.subplots(2,1,figsize=(11,7.2))
    for ax, profile in zip(axes, ('smoke','performance')):
        selected = [r for r in rows if r['profile']==profile and r['attempt'] is not None]
        for row in selected:
            x, y = row['attempt'],row['suite_median'];cat=category(row)
            if row['suite_min'] is not None:
                ax.vlines(x,row['suite_min'],row['suite_max'],color=colors[cat],alpha=.6,lw=1)
            ax.scatter(x,y,color=colors[cat],marker='x' if cat=='revert' else 'o',s=34,zorder=3)
            if x==34:ax.annotate('coverage failure', (x,y),xytext=(x-7,y-3),fontsize=8,arrowprops={'arrowstyle':'->','lw':.8})
        for cat in colors:
            ax.scatter([],[],color=colors[cat],marker='x' if cat=='revert' else 'o',label=cat)
        ax.set(title=f'{profile.capitalize()} profile — {14 if profile=="smoke" else 11} fixed instances',xlabel='Optimization attempt (0 = original smoke baseline)',ylabel='Suite wall time (s)')
        ax.grid(alpha=.25);ax.legend(ncol=4,fontsize=8)
        for x in ([20.5,25.5] if profile=='smoke' else []):ax.axvline(x,color='gray',ls=':',lw=1)
    fig.suptitle('Recorded attempt wall times: medians and observed repetition ranges\nSeparate profiles; rounds span different sessions and correctness revisions',fontsize=12)
    save(fig,'attempt-wall-times')

    fig, axes = plt.subplots(2,1,figsize=(11,6.5))
    for ax,profile in zip(axes,('smoke','performance')):
        for row in rows:
            if row['profile']!=profile or row['attempt'] in (None,0) or row['parent_speedup'] is None:continue
            x,y=row['attempt'],row['parent_speedup'];cat=category(row)
            if row['ci_low'] is not None:ax.vlines(x,row['ci_low'],row['ci_high'],color=colors[cat],alpha=.6)
            ax.scatter(x,y,color=colors[cat],marker='x' if cat=='revert' else 'o',s=28)
        ax.axhline(1,color='black',ls='--',lw=1);ax.set(yscale='log',ylabel='Search speedup vs parent',xlabel='Attempt',title=f'{profile.capitalize()}: >1 is faster; intervals shown when recorded')
        ax.grid(alpha=.25)
    save(fig,'attempt-search-speedups')

    milestones=[('Original','outputs/performance/round1/baseline/summary.json'),('A1: h-cache','outputs/performance/round1/attempt1/summary.json'),('A5: joint bounds','outputs/performance/round1/attempt5/summary.json'),('A20: graph bounds','outputs/performance/round4/attempt20/summary.json'),('A27: early rejection','outputs/performance/round6/attempt27/summary.json'),('A36: cache access','outputs/performance/round8/attempt36/summary.json')]
    data=[read(path)['search_medians'] for _,path in milestones];cases=sorted(data[0]);assert all(set(d)==set(cases) for d in data)
    matrix=np.array([[data[0][case]/d[case] for case in cases] for d in data])
    fig,ax=plt.subplots(figsize=(11.6,4.2));im=ax.imshow(np.log2(matrix),aspect='auto',cmap='Blues',vmin=0)
    ax.set_yticks(range(len(data)),[label for label,_ in milestones]);ax.set_xticks(range(len(cases)),cases,rotation=50,ha='right',fontsize=8)
    for i in range(len(data)):
        for j in range(len(cases)):ax.text(j,i,f'{matrix[i,j]:.1f}',ha='center',va='center',fontsize=7,color='white' if np.log2(matrix[i,j])>np.log2(matrix).max()*.6 else 'black')
    fig.colorbar(im,ax=ax,label='log₂ speedup over original smoke baseline')
    ax.set_title('Per-instance cumulative search speedups (labels give × ratios)\nA20→A27 spans correctness fixes; cross-session comparisons are descriptive',fontsize=10)
    save(fig,'smoke-milestone-heatmap')
    with (OUTPUT/'heatmap-data.csv').open('w',newline='') as file:
        writer=csv.writer(file);writer.writerow(['milestone','source','instance','median_search_seconds','speedup_original'])
        for i,(label,path) in enumerate(milestones):
            for case in cases:writer.writerow([label,path,case,data[i][case],data[0][case]/data[i][case]])

    fig,axes=plt.subplots(1,2,figsize=(10.5,4.2))
    labels=['UP + FD / hmax','Direct + FD / hmax','UP + FD / LM-cut','Direct + FD / LM-cut']
    search=[9.949,9.618,8.447,8.037];prep=[30.601,1.730,29.703,1.725];wall=[27.295,17.969,26.619,18.052]
    x=np.arange(4);axes[0].bar(x,prep,label='Preprocessing',color='#999999');axes[0].bar(x,search,bottom=prep,label='Search',color='#0072B2')
    axes[0].set(ylabel='Sum of per-instance medians (s)',title='Attempt 59: direct compilation');axes[0].legend(fontsize=8)
    axes[1].bar(x,wall,color=['#999999','#0072B2','#999999','#D55E00']);axes[1].set(ylabel='Median suite wall time (s)',title='Actual concurrent suite, including replay')
    for ax in axes:ax.set_xticks(x,labels,rotation=30,ha='right',fontsize=8);ax.grid(axis='y',alpha=.2)
    save(fig,'direct-compilation-phases')
    (OUTPUT/'migration-phase-data.json').write_text(json.dumps({'source':'docs/performance-log.md, attempt 59 paired repeated controls','labels':labels,'sum_median_search':search,'sum_median_preprocessing':prep,'suite_wall_median':wall},indent=2)+'\n')

    coverage = OUTPUT.parent / 'prebranch-comparison/coverage/coverage-over-time.png'
    if coverage.exists():
        figure, axis = plt.subplots(figsize=(9,6))
        axis.imshow(plt.imread(coverage)); axis.axis('off'); figure.tight_layout()
        figures.append(figure)

    # A portable, self-contained PDF report: wrapped narrative followed by figures.
    narrative=(ROOT/'docs/performance-report.md').read_text()
    lines=[]
    for line in narrative.splitlines():
        if line.startswith('!['):continue
        if line.startswith('|'):
            cells = [cell.strip() for cell in line.strip('|').split('|')]
            if cells[0] == 'Mechanism' or all(set(cell) <= {'-', ':', ' '} for cell in cells):
                continue
            line = cells[0] + '. Evidence: ' + cells[1] + '. ' + cells[2]
            lines.append('')
        line=re.sub(r'\[([^]]+)\]\([^)]+\)',r'\1',line).replace('**','').replace('`','').lstrip('#')
        lines.extend(textwrap.wrap(line,width=98) or [''])
    with PdfPages(OUTPUT/'performance-report.pdf') as pdf:
        for offset in range(0,len(lines),49):
            page=plt.figure(figsize=(8.27,11.69));page.text(.07,.95,'\n'.join(lines[offset:offset+49]),va='top',fontsize=9,fontfamily='DejaVu Sans',linespacing=1.5)
            pdf.savefig(page);plt.close(page)
        for figure in figures:pdf.savefig(figure)
    for figure in figures:plt.close(figure)
    (OUTPUT/'report-metadata.json').write_text(json.dumps({'attempt_rows':len(rows),'figures':['attempt-wall-times','attempt-search-speedups','smoke-milestone-heatmap','direct-compilation-phases'],'source_log':'docs/performance-log.md','failures':'Attempt 34 plotted as failed wall time, excluded from speedup aggregates.','ranges':'Observed min/max repetitions, not confidence intervals; absent or incompatible ranges omitted.','bootstrap':'Search-speedup intervals copied from recorded whole-run bootstraps where available.','profile_boundary':'Attempts 1–40 smoke; 41–55 performance. Migration 56–61 evaluated separately.','milestones':milestones},indent=2)+'\n')
    print(f'Generated report and four figures in {OUTPUT}; {len(rows)} attempt/reference/refinement records.')


if __name__=='__main__':
    generate()

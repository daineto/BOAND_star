"""Figures for the fixed pilot and explicitly adaptive follow-up."""
import argparse
import csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT=Path(__file__).resolve().parents[2]

def create(pilot_analysis, output):
    base=output; base.mkdir(parents=True, exist_ok=True); rows=list(csv.DictReader(open(pilot_analysis/'runs.csv')))
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for config in ('FD hmax','FD lmcut'):
     r=sorted((r for r in rows if r['configuration']==config and r['family']=='corner'),key=lambda r:int(r['height']))
     heights=[int(x['height']) for x in r]
     axes[0].plot(heights,[float(x['search_seconds']) for x in r],'-o',label=config)
     axes[1].plot(heights,[int(x['expansions']) for x in r],'-o',label=config)
    axes[0].set(xlabel='Corner-grid height (width = 3)',ylabel='Completed search time (s)',yscale='log')
    axes[1].set(xlabel='Corner-grid height (width = 3)',ylabel='Expansions',yscale='log')
    for ax in axes:ax.legend();ax.grid(alpha=.2)
    fig.suptitle('Corner family: two-point fronts at every tested height; single measurements')
    fig.tight_layout()
    for ext in ('png','pdf','svg'):fig.savefig(base/f'corner-scaling.{ext}',dpi=180)
    plt.close(fig)
    main=json.load(open(ROOT/'benchmarks/journal_tradeoffs/frozenlake/generation.json'))['instances'];supp=json.load(open(ROOT/'benchmarks/journal_tradeoffs/frozenlake_supplemental/generation.json'))['instances'];records={r['instance']:r for r in main+supp}
    fig,axes=plt.subplots(1,3,figsize=(10,5))
    fronts={'verified-03':[(2,10),(3,4)],'mixed-4x4-s23-a5':[(2,'∞'),(3,3)],'corner-3x10-s0':[(1,21),(11,19)]}
    for ax,name in zip(axes,fronts):
     item=records[name];w,h=item['width'],item['height']
     for x,y,k in item['cells']:
      ax.add_patch(Rectangle((x,y),1,1,facecolor={'ice':'#dceff6','wall':'#444444','pit':'#b14d49'}[k],edgecolor='white',linewidth=1))
      symbol='S' if [x,y]==item['start'] else 'G' if [x,y]==item['goal'] else ''
      if symbol:ax.text(x+.5,y+.5,symbol,ha='center',va='center',fontweight='bold',fontsize=13)
     ax.set(xlim=(0,w),ylim=(0,h),aspect='equal');ax.set_xticks([]);ax.set_yticks([])
     for spine in ax.spines.values():spine.set_linewidth(4);spine.set_color('#444444')
     ax.set_title(name+'\n'+', '.join(f'({b}, {v})' for b,v in fronts[name]),fontsize=11,pad=10)
    fig.text(.5,.02,'S: start    G: goal    Blue: ice    Dark: wall    Costs: (best case, worst case)',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.06,1,1))
    for ext in ('png','pdf','svg'):fig.savefig(base/f'quality-examples.{ext}',dpi=180)
    print('Figures generated')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot-analysis", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args=p.parse_args()
    create(args.pilot_analysis, args.output)

if __name__ == "__main__":
    main()

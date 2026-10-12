import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
from pathlib import Path
from .core import ROOT,NICHE,approved_niche,config,decode_marker,draft,encode_marker,research
from .render import render

def gh(*args):
    return subprocess.run(['gh',*args],text=True,check=True,capture_output=True).stdout.strip()

def create_labels():
    for label,color in [('awaiting-niche','f6b26b'),('awaiting-review','dedede'),
                        ('niche-approved','2da44e'),('publish-approved','2da44e')]:
        gh('label','create',label,'--color',color,'--force')

def issue_niches(path):
    create_labels()
    existing=json.loads(gh('issue','list','--label','awaiting-niche',
                           '--state','open','--json','number'))
    if existing:
        print('An unreviewed niche issue already exists; skipping duplicates')
        return
    for p in json.loads(Path(path).read_text())[:config()['max_issues_per_run']]:
        signals=''.join(f"- {x['title']} — {x['url']}\n" for x in p['sources'])
        body=(f"# Proposed niche: {p['name']}\n\n"
              f"**Why consider it:** {p['why']}\n\n"
              f"**Original video angle:** {p['original_angle']}\n\n"
              f"**Potential monetization (not active):** {p['monetization']}\n\n"
              f"**Risks:** {p['risks']}\n\n"
              "## RSS headlines used as signals\n"+signals+
              "\nTo select this niche, the repository owner should apply "
              "the **niche-approved** label to this Issue. No uploads occur automatically.\n\n"
              +encode_marker('NICHE',{k:p[k] for k in ('id','name','query')}))
        gh('issue','create','--title','Niche decision: '+p['name'],
           '--label','awaiting-niche','--body',body)
        print('Created niche proposal:',p['name'])

def issue_draft(draft_path,video_path):
    create_labels()
    item=json.loads(Path(draft_path).read_text())
    run=os.environ['GITHUB_RUN_ID']
    digest=hashlib.sha256(Path(video_path).read_bytes()).hexdigest()
    provenance={'run_id':int(run),'draft_id':item['id'],'sha256':digest}
    script='\n\n'.join(f"### {i+1}. {s['headline']}\n{s['narration']}"
                       for i,s in enumerate(item['scenes']))
    source_list='\n'.join('- '+x for x in item['source_urls'])
    body=(f"# {item['title']}\n\n"
          f"**Format:** {item['format']} | **Words:** {item['word_count']}\n\n"
          f"**Preview exact rendered video:** [Download draft-{run} artifact from the run]"
          f"(https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{run}).\n\n"
          f"## Script for approval\n{script}\n\n"
          f"## YouTube description\n{item['description']}\n\n"
          f"## Research signals\n{source_list}\n\n"
          f"## Human fact-check notes\n{item.get('risk_notes','None')}\n\n"
          "**Publishing is disabled until owner approval.** After watching the artifact, "
          "apply the **publish-approved** label to request an upload of this exact "
          "SHA-256-verified video. It will default to PRIVATE even after approval. "
          "To reject, close this Issue.\n\n"+encode_marker('DRAFT',provenance))
    gh('issue','create','--title','Review '+item['format']+': '+item['title'],
       '--label','awaiting-review','--body',body)
    print('Opened video approval Issue:',item['id'])

def get_event():
    return json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())

def verify_owner_event(event,expected_label):
    if event.get('action')!='labeled' or event.get('label',{}).get('name')!=expected_label:
        raise RuntimeError('No valid explicit approval label event')
    if event.get('sender',{}).get('login','').lower()!=os.environ['GITHUB_REPOSITORY'].split('/')[0].lower():
        raise RuntimeError('Only the repository owner can approve')
    if event.get('issue',{}).get('user',{}).get('login')!='github-actions[bot]':
        raise RuntimeError('Only Actions-generated review issues may be approved')

def accept_niche():
    event=get_event()
    verify_owner_event(event,'niche-approved')
    chosen=decode_marker(event['issue']['body'],'NICHE')
    known={x['id']:x for x in config()['candidate_niches']}
    if chosen.get('id') not in known or any(chosen.get(k)!=known[chosen['id']][k]
                                           for k in ('id','name','query')):
        raise RuntimeError('Niche marker does not match known settings')
    if approved_niche().get('id'):
        raise RuntimeError('A niche is already approved. No automated replacement.')
    NICHE.write_text(json.dumps(chosen,indent=2)+'\n')
    print('Approved selected niche:',chosen['name'])

def publish_approved(output):
    event=get_event()
    verify_owner_event(event,'publish-approved')
    marker=decode_marker(event['issue']['body'],'DRAFT')
    run=str(marker.get('run_id',''))
    if not run.isdigit() or not str(marker.get('draft_id','')).replace('-','').isalnum():
        raise RuntimeError('Invalid artifact provenance')
    dest=Path(output);dest.mkdir(parents=True,exist_ok=True)
    gh('run','download',run,'-n','draft-'+run,'-D',str(dest))
    item=json.loads((dest/'draft.json').read_text())
    if item.get('id')!=marker['draft_id']:
        raise RuntimeError('Draft identifier mismatch')
    video=dest/'video.mp4'
    if hashlib.sha256(video.read_bytes()).hexdigest()!=marker.get('sha256'):
        raise RuntimeError('Video hash mismatch: upload blocked')
    for k in ['YT_CLIENT_ID','YT_CLIENT_SECRET','YT_REFRESH_TOKEN']:
        if not os.getenv(k): raise RuntimeError(f'Missing {k}: upload blocked')
    from .youtube import upload
    result=upload(video,item)
    print('UPLOAD_RESULT_JSON='+json.dumps(result))
    return result

def main():
    p=argparse.ArgumentParser(description='No-spend, approval-first content autopilot')
    p.add_argument('command',choices=['research','issue-niches','draft','render','issue-draft',
                                     'accept-niche','publish-approved','dryrun'])
    p.add_argument('--input');p.add_argument('--output')
    args=p.parse_args()
    conf=config()
    if args.command=='research':
        if approved_niche().get('id'):
            print('Niche already approved; skipping research');return
        results=research()
        Path(args.output or 'niche-proposals.json').write_text(json.dumps(results,indent=2))
    elif args.command=='issue-niches':
        issue_niches(args.input)
    elif args.command=='draft':
        niche=approved_niche()
        if not niche.get('id'):
            print('Niche not approved; no draft generated');return
        mix=conf['content_mix']
        kind=mix[dt.date.today().toordinal()%len(mix)]
        item=draft(niche,kind)
        dest=Path(args.output or 'work/draft.json')
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(item,indent=2,ensure_ascii=False))
        print('Created draft',item['id'],kind)
    elif args.command=='render':
        print(render(args.input,args.output or 'work/rendered'))
    elif args.command=='issue-draft':
        issue_draft(args.input,args.output)
    elif args.command=='accept-niche':
        accept_niche()
    elif args.command=='publish-approved':
        publish_approved(args.output or 'work/approved')
    elif args.command=='dryrun':
        print(render(ROOT/'demo/sample_draft.json',args.output or 'work/demo'))

if __name__=='__main__': main()

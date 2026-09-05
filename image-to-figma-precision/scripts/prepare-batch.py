"""Prepare a bounded use_figma script from a reviewed plan and saved node state.
This does not contact Figma. Execute generated JS using the authorized Figma tool,
then merge the returned mapping/IDs into state before preparing the next batch.
"""
import argparse,json,hashlib
from pathlib import Path

def validate_transparent_asset(key, asset):
    report=asset.get('alphaReport',{})
    review=asset.get('visualReview',{})
    if not asset.get('imageHash') or not asset.get('sha256'):
        raise ValueError('Missing uploaded transparent asset: '+key)
    if report.get('rawGate')!='pass' or not report.get('hasAlpha') or report.get('sourceSha256')!=asset['sha256']:
        raise ValueError('Missing/mismatched Alpha evidence: '+key)
    source=Path(report.get('file',''))
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=asset['sha256']:
        raise ValueError('Transparent asset file missing/changed: '+key)
    if review.get('status')!='pass' or not {'white','black','magenta'}.issubset(review.get('backgrounds',[])):
        raise ValueError('Missing three-background visual review: '+key)
    if not all(review.get('checks',{}).get(k)=='pass' for k in ['smoothEdges','noMatte','highlightsPreserved','holesCorrect']):
        raise ValueError('Incomplete cutout quality review: '+key)
    semantic=asset.get('semanticReport',{})
    if asset.get('semanticContract') and (semantic.get('pass') is not True or semantic.get('imageSha256')!=asset['sha256']):
        raise ValueError('Missing/mismatched semantic evidence: '+key)
    evidence=review.get('evidenceFiles',[])
    if not evidence or not all(Path(p).is_file() for p in evidence):
        raise ValueError('Missing visual evidence files: '+key)

def prepare(plan, state, template, count=8):
    if not 1<=count<=10:raise ValueError('Batch size must be between 1 and 10')
    keys=[s['key'] for s in plan]
    if len(keys)!=len(set(keys)):raise ValueError('Duplicate element keys')
    nodes=state.get('nodes',{})
    positions={'root':[0,0]}
    positions.update({s['key']:s['box'] for s in plan})
    batch=[s for s in plan if s['key'] not in nodes][:count]
    known=set(nodes)
    for s in batch:
        if s.get('requiresTransparency') and 'crop' in s:
            raise ValueError('Raw crop is not a transparent icon: '+s['key'])
        if s.get('requiresTransparency') and not s.get('transparentAsset'):
            raise ValueError('Transparent foreground is not ready: '+s['key'])
        if s.get('transparentAsset'):
            if 'crop' in s:raise ValueError('Do not mix transparent asset with source crop: '+s['key'])
            validate_transparent_asset(s['key'],state.get('assets',{}).get(s['transparentAsset'],{}))
        if s['parent'] not in known:raise ValueError('Missing or out-of-order parent: '+s['parent'])
        if s['type'] not in ['FRAME','COMPONENT','RECTANGLE','VECTOR','TEXT']:
            raise ValueError('Unsupported type: '+s['type'])
        if len(s['box'])!=4 or min(s['box'][2:])<=0:raise ValueError('Invalid box: '+s['key'])
        if s['type']=='TEXT' and not all(k in s for k in ['text','family','style','size']):
            raise ValueError('Missing text/font specification: '+s['key'])
        known.add(s['key'])
    prefix='const '+','.join(k+'='+json.dumps(v,ensure_ascii=False) for k,v in {
        'batch':batch,'state':nodes,'positions':positions,'colors':state.get('colors',{}),'assets':state.get('assets',{}),
        'config':{k:state[k] for k in ['pageId','sourceHash','sourceWidth','sourceHeight']}
    }.items())+';\n'
    return prefix+template,len(batch)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan');p.add_argument('state');p.add_argument('--count',type=int,default=8);p.add_argument('--out',required=True)
    a=p.parse_args();directory=Path(__file__).parent
    try:
        code,count=prepare(json.loads(Path(a.plan).read_text(encoding='utf-8-sig')),
            json.loads(Path(a.state).read_text(encoding='utf-8-sig')),
            (directory/'apply-batch.js').read_text(encoding='utf-8'),a.count)
    except ValueError as error:
        # Invalidate a previous batch file rather than leave stale executable writes.
        Path(a.out).write_text('throw new Error('+json.dumps(str(error),ensure_ascii=False)+');\n',encoding='utf-8')
        raise SystemExit(str(error))
    Path(a.out).write_text(code,encoding='utf-8')
    print(json.dumps({'prepared':count,'output':str(Path(a.out).resolve())}))

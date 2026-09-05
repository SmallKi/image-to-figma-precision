"""Compare actual 1x Figma export against source without scaling/alignment.
Requires Pillow and numpy. Metrics are pixel error, NOT a similarity score.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rgb(path):
    im = Image.open(path).convert('RGBA')
    bg = Image.new('RGBA', im.size, 'white')
    return Image.alpha_composite(bg, im).convert('RGB')

def metrics(a, b):
    d = np.abs(a.astype(np.float32)-b.astype(np.float32))
    return {'mae_255':round(float(d.mean()),4),
            'rmse_255':round(float(np.sqrt((d*d).mean())),4),
            'pixels_over_16_fraction':round(float((d.max(axis=2)>16).mean()),6),
            'max_channel_error':int(d.max())}

def compare(reference, candidate, manifest, output):
    a,b=rgb(reference),rgb(candidate)
    if a.size != b.size:
        raise ValueError(f'Export size mismatch: source={a.size}, candidate={b.size}; export at 1x, do not rescale.')
    aa,bb=np.array(a),np.array(b)
    report={'reference_sha256':digest(reference),'candidate_sha256':digest(candidate),
            'dimensions':list(a.size),'global':metrics(aa,bb),'regions':{}}
    for r in manifest.get('regions',[]):
        x,y,w,h=r['box']
        if any(int(v)!=v for v in [x,y,w,h]) or x<0 or y<0 or w<=0 or h<=0 or x+w>a.width or y+h>a.height:
            raise ValueError(f'Invalid region: {r}')
        report['regions'][r['key']]=metrics(aa[y:y+h,x:x+w],bb[y:y+h,x:x+w])
    all_metrics=[report['global'],*report['regions'].values()]
    report['pixel_gate_pass']=all(m['mae_255']<=3 and m['pixels_over_16_fraction']<=.01 for m in all_metrics)
    report['note']='Pixel gate only; native text, components, occlusion and visual review are separate mandatory gates.'
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    Image.blend(a,b,.5).save(output/'overlay.png')
    d=np.abs(aa.astype(np.int16)-bb.astype(np.int16)).max(axis=2)
    heat=np.zeros_like(aa);heat[:,:,0]=np.minimum(d*5,255).astype('uint8')
    Image.fromarray(heat).save(output/'difference.png')
    (output/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference');p.add_argument('candidate');p.add_argument('--regions');p.add_argument('--out',required=True)
    args=p.parse_args()
    manifest=json.loads(Path(args.regions).read_text(encoding='utf-8-sig')) if args.regions else {}
    print(json.dumps(compare(args.reference,args.candidate,manifest,args.out),ensure_ascii=False,indent=2))

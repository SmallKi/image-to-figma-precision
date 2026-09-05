"""Check semantic anchors and edge-policy diagnostics on a real cutout.

The script never modifies pixels. Edge rules are opt-in because pixel-art and
antialiased artwork have different valid boundaries; put the chosen thresholds
in the reviewed contract instead of hard-coding one rule for every icon.
Contract boxes use candidate pixel coordinates. Registration and semantic
selection must be visually verified; passing anchors do not certify all edges.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
from collections import deque

def inspect(image,contract,source=None):
    path=Path(image)
    with Image.open(path) as im:
        real_alpha='A' in im.getbands() or 'transparency' in im.info
        rgba=np.asarray(im.convert('RGBA'));size=list(im.size)
    failures=[];checks=[]
    if size!=contract['size']: failures.append('registration_size_mismatch')
    if not real_alpha: failures.append('no_alpha_channel')
    if failures:return {'pass':False,'failures':failures,'size':size,'checks':[]}
    alpha=rgba[:,:,3]/255
    coverage=float((alpha>.01).mean())
    coverage_policy=contract.get('alphaCoverage',{})
    if coverage_policy:
        minimum=float(coverage_policy.get('min',0))
        maximum=float(coverage_policy.get('max',1))
        coverage_pass=minimum<=coverage<=maximum
        checks.append({'kind':'coverage','name':'foreground_alpha_coverage','fraction':coverage,
                       'minimum':minimum,'maximum':maximum,'pass':coverage_pass})
        if not coverage_pass:failures.append('coverage:foreground_fraction_out_of_range')
        if 'minOpaqueFractionOfForeground' in coverage_policy:
            foreground=alpha>.01
            opaque_fraction=float((alpha[foreground]>=.98).mean()) if foreground.any() else 0.0
            min_opaque=float(coverage_policy['minOpaqueFractionOfForeground'])
            opaque_pass=opaque_fraction>=min_opaque
            checks.append({'kind':'coverage','name':'opaque_subject_interior','fraction':opaque_fraction,
                           'minimum':min_opaque,'pass':opaque_pass})
            if not opaque_pass:failures.append('coverage:subject_interior_too_translucent')

    source_integrity=None
    if source:
        with Image.open(source) as sim:
            source_rgba=np.asarray(sim.convert('RGBA'))
            source_size=list(sim.size)
        if source_size!=size:
            failures.append('source_registration_size_mismatch')
        else:
            policy=contract.get('sourceRgbIntegrity',{})
            min_alpha=float(policy.get('minAlpha',.98))
            max_mae=float(policy.get('maxMae',1.0))
            max_bad=float(policy.get('maxBadFraction',.01))
            tolerance=float(policy.get('channelTolerance',2))
            keep=alpha>=min_alpha
            if keep.any():
                delta=np.abs(rgba[:,:,:3].astype(np.int16)-source_rgba[:,:,:3].astype(np.int16))
                mae=float(delta[keep].mean())
                bad=float((delta.max(axis=2)[keep]>tolerance).mean())
                passed=mae<=max_mae and bad<=max_bad
            else:
                mae=None;bad=1.0;passed=False
            source_integrity={'kind':'fidelity','name':'opaque_rgb_matches_registered_source',
                              'mae':mae,'badFraction':bad,'pass':passed}
            checks.append(source_integrity)
            if not passed:failures.append('fidelity:opaque_rgb_changed')
    empty=alpha<.5;seen=np.zeros(empty.shape,dtype=bool);holes=[]
    for yy,xx in zip(*np.where(empty)):
        if seen[yy,xx]:continue
        queue=deque([(int(xx),int(yy))]);seen[yy,xx]=True;points=[];touches=False
        while queue:
            x,y=queue.popleft();points.append((x,y));touches|=x==0 or y==0 or x==size[0]-1 or y==size[1]-1
            for nx,ny in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
                if 0<=nx<size[0] and 0<=ny<size[1] and empty[ny,nx] and not seen[ny,nx]:seen[ny,nx]=True;queue.append((nx,ny))
        if not touches:
            xs,ys=zip(*points);holes.append({'pixels':len(points),'box':[min(xs),min(ys),max(xs)-min(xs)+1,max(ys)-min(ys)+1]})
    if 'expectedEnclosedHoles' in contract and len(holes)!=contract['expectedEnclosedHoles']:failures.append('unexpected_enclosed_hole_count')

    # Disconnected opaque fragments often reveal carried background debris. The
    # expected count is object-specific because sparks, leaves and separate
    # decorations may be legitimate components.
    solid=alpha>=.5;seen_solid=np.zeros(solid.shape,dtype=bool);components=[]
    for yy,xx in zip(*np.where(solid)):
        if seen_solid[yy,xx]:continue
        queue=deque([(int(xx),int(yy))]);seen_solid[yy,xx]=True;points=[]
        while queue:
            x,y=queue.popleft();points.append((x,y))
            for nx,ny in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
                if 0<=nx<size[0] and 0<=ny<size[1] and solid[ny,nx] and not seen_solid[ny,nx]:
                    seen_solid[ny,nx]=True;queue.append((nx,ny))
        xs,ys=zip(*points)
        components.append({'pixels':len(points),'box':[min(xs),min(ys),max(xs)-min(xs)+1,max(ys)-min(ys)+1]})
    components.sort(key=lambda item:item['pixels'],reverse=True)
    component_policy=contract.get('componentPolicy',{})
    if component_policy:
        minimum=int(component_policy.get('minCount',0))
        maximum=int(component_policy.get('maxCount',10**9))
        count_pass=minimum<=len(components)<=maximum
        checks.append({'kind':'components','name':'foreground_component_count','count':len(components),
                       'minimum':minimum,'maximum':maximum,'pass':count_pass})
        if not count_pass:failures.append('components:unexpected_foreground_component_count')
        tiny_limit=int(component_policy.get('tinyComponentMaxPixels',0))
        max_tiny=int(component_policy.get('maxTinyComponents',10**9))
        tiny=[item for item in components if item['pixels']<=tiny_limit] if tiny_limit>0 else []
        tiny_pass=len(tiny)<=max_tiny
        checks.append({'kind':'components','name':'tiny_foreground_fragments','count':len(tiny),
                       'pixelThreshold':tiny_limit,'maximum':max_tiny,'pass':tiny_pass})
        if not tiny_pass:failures.append('components:tiny_foreground_fragments')
    for kind in ['keep','holes','outside']:
        for zone in contract.get(kind,[]):
            x,y,w,h=zone['box']
            if any(int(v)!=v for v in [x,y,w,h]) or x<0 or y<0 or w<=0 or h<=0 or x+w>size[0] or y+h>size[1]:raise ValueError('Invalid region: '+zone['name'])
            a=alpha[y:y+h,x:x+w]
            if kind=='keep':
                bad=float(np.mean(a<zone.get('minAlpha',.98)))
                passed=bad<=zone.get('maxBadFraction',0)
            else:
                bad=float(np.mean(a>zone.get('maxAlpha',.02)))
                passed=bad<=zone.get('maxBadFraction',0)
            checks.append({'kind':kind,'name':zone['name'],'badFraction':bad,'pass':passed})
            if not passed:failures.append(kind+':'+zone['name'])
    foreground=alpha>.01
    edge=foreground.copy()
    edge[1:-1,1:-1]&=~(foreground[:-2,1:-1]&foreground[2:,1:-1]&foreground[1:-1,:-2]&foreground[1:-1,2:])
    partial=(alpha>0)&(alpha<1)
    edge_partial=edge&partial
    policy=contract.get('edgePolicy',{})
    partial_pixels=int(partial.sum())
    edge_pixels=int(edge.sum())
    partial_boundary_fraction=float(edge_partial.sum()/edge_pixels) if edge_pixels else 0.0
    # These diagnostics catch several defects that a simple partial-alpha count
    # misses: a one-pixel spike can still be antialiased, a pinhole can sit inside
    # an otherwise valid body, and a quantized/abrupt edge can have some partial
    # pixels while still looking visibly rough at 4x. They are opt-in because
    # deliberate pixel art and thin detached decorations need different limits.
    padded_solid=np.pad(solid,((1,1),(1,1)),constant_values=False)
    solid_neighbors=sum(
        padded_solid[1+dy:1+dy+solid.shape[0],1+dx:1+dx+solid.shape[1]]
        for dy in (-1,0,1) for dx in (-1,0,1) if (dx,dy)!=(0,0)
    )
    single_pixel_spurs=int((solid&(solid_neighbors<=1)).sum())
    single_pixel_notches=int((~solid&(solid_neighbors>=7)).sum())
    padded_partial=np.pad(partial,((1,1),(1,1)),constant_values=False)
    partial_neighbors=sum(
        padded_partial[1+dy:1+dy+partial.shape[0],1+dx:1+dx+partial.shape[1]]
        for dy in (-1,0,1) for dx in (-1,0,1) if (dx,dy)!=(0,0)
    )
    isolated_partial=int((partial&(partial_neighbors==0)).sum())
    isolated_partial_fraction=float(isolated_partial/partial_pixels) if partial_pixels else 1.0
    alpha_levels=int(np.unique(rgba[:,:,3][partial]).size) if partial_pixels else 0
    transitions=np.concatenate((np.abs(alpha[:,1:]-alpha[:,:-1]).ravel(),
                                np.abs(alpha[1:,:]-alpha[:-1,:]).ravel()))
    transitions=transitions[transitions>(1/255)]
    abrupt_transition_fraction=float((transitions>=.95).mean()) if transitions.size else 1.0
    if policy:
        min_pixels=int(policy.get('minPartialAlphaPixels',0))
        min_fraction=float(policy.get('minPartialAlphaBoundaryFraction',0))
        smooth_pass=partial_pixels>=min_pixels and partial_boundary_fraction>=min_fraction
        checks.append({'kind':'edge','name':'antialiased_boundary','partialAlphaPixels':partial_pixels,
                       'partialAlphaOnBoundaryFraction':partial_boundary_fraction,'pass':smooth_pass})
        if not smooth_pass:failures.append('edge:hard_or_insufficient_antialiasing')
        matte=policy.get('forbiddenMatteColors',[])
        if matte and edge_partial.any():
            rgb=rgba[:,:,:3].astype(np.float32)
            distances=[]
            for color in matte:
                c=np.asarray(color['rgb'],dtype=np.float32)
                distances.append(np.sqrt(((rgb-c)**2).sum(axis=2)))
            nearest=np.minimum.reduce(distances)
            radius=float(policy.get('matteDistance',24))
            contaminated=edge_partial&(nearest<=radius)
            fraction=float(contaminated.sum()/edge_partial.sum())
            max_fraction=float(policy.get('maxMatteFraction',.02))
            matte_pass=fraction<=max_fraction
            checks.append({'kind':'edge','name':'forbidden_matte_color','badFraction':fraction,
                           'matchingPixels':int(contaminated.sum()),'pass':matte_pass})
            if not matte_pass:failures.append('edge:forbidden_matte_color')
        elif matte:
            checks.append({'kind':'edge','name':'forbidden_matte_color','badFraction':0,
                           'matchingPixels':0,'pass':False})
            failures.append('edge:matte_check_without_partial_boundary')
        quality_fields={'minPartialAlphaLevels','maxAbruptTransitionFraction',
                        'maxIsolatedPartialAlphaFraction','maxSinglePixelSpurs','maxSinglePixelNotches'}
        if quality_fields.intersection(policy):
            minimum_levels=int(policy.get('minPartialAlphaLevels',0))
            maximum_abrupt=float(policy.get('maxAbruptTransitionFraction',1))
            maximum_isolated=float(policy.get('maxIsolatedPartialAlphaFraction',1))
            maximum_spurs=int(policy.get('maxSinglePixelSpurs',10**9))
            maximum_notches=int(policy.get('maxSinglePixelNotches',10**9))
            quality_pass=(alpha_levels>=minimum_levels and abrupt_transition_fraction<=maximum_abrupt
                          and isolated_partial_fraction<=maximum_isolated
                          and single_pixel_spurs<=maximum_spurs and single_pixel_notches<=maximum_notches)
            checks.append({'kind':'edge','name':'boundary_continuity','partialAlphaLevels':alpha_levels,
                           'minimumPartialAlphaLevels':minimum_levels,
                           'abruptTransitionFraction':abrupt_transition_fraction,
                           'maximumAbruptTransitionFraction':maximum_abrupt,
                           'isolatedPartialAlphaPixels':isolated_partial,
                           'isolatedPartialAlphaFraction':isolated_partial_fraction,
                           'maximumIsolatedPartialAlphaFraction':maximum_isolated,
                           'singlePixelSpurs':single_pixel_spurs,'maximumSinglePixelSpurs':maximum_spurs,
                           'singlePixelNotches':single_pixel_notches,'maximumSinglePixelNotches':maximum_notches,
                           'pass':quality_pass})
            if not quality_pass:failures.append('edge:boundary_continuity')
    return {'pass':not failures,'failures':failures,'checks':checks,'size':size,'alphaCoverageFraction':coverage,
            'sourceRgbIntegrity':source_integrity,'enclosedTransparentRegions':holes,
            'foregroundConnectedRegions':components,
            'imageSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'edgeDiagnostics':{'edgePixels':edge_pixels,'partialAlphaPixels':partial_pixels,
            'partialAlphaOnBoundaryFraction':partial_boundary_fraction,'partialAlphaLevels':alpha_levels,
            'abruptTransitionFraction':abrupt_transition_fraction,
            'isolatedPartialAlphaPixels':isolated_partial,
            'isolatedPartialAlphaFraction':isolated_partial_fraction,
            'singlePixelSpurs':single_pixel_spurs,'singlePixelNotches':single_pixel_notches},
            'visualGate':'required','limits':'Configured edge rules catch hard masks, known matte colors and mostly translucent subjects; anchors catch missing highlights and filled holes; component rules catch unexpected opaque fragments. Unknown matte colors, silhouette drift, local jaggies and texture still need registered source and multi-background visual comparison.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('image');p.add_argument('contract');p.add_argument('--source');p.add_argument('--out',required=True);a=p.parse_args()
    report=inspect(a.image,json.loads(Path(a.contract).read_text(encoding='utf-8')),a.source)
    Path(a.out).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False));raise SystemExit(0 if report['pass'] else 1)

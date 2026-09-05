"""Render a repeatable multi-background and alpha proof sheet for one RGBA cutout."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


BACKGROUNDS = [
    ("WHITE", (255, 255, 255)),
    ("BLACK", (0, 0, 0)),
    ("MAGENTA", (255, 0, 255)),
    ("CYAN", (0, 255, 255)),
]


def composite(rgba, color):
    bg = Image.new("RGBA", rgba.size, (*color, 255))
    return Image.alpha_composite(bg, rgba).convert("RGB")


def render(image_path, out_path, zoom=1):
    image_path=Path(image_path);out_path=Path(out_path)
    with Image.open(image_path) as im:
        real_alpha='A' in im.getbands() or 'transparency' in im.info
        rgba=im.convert('RGBA')
    if not real_alpha:
        raise ValueError('Input has no real alpha channel')
    if zoom!=1:
        rgba=rgba.resize((rgba.width*zoom,rgba.height*zoom),Image.Resampling.NEAREST)
    arr=np.asarray(rgba);alpha=arr[:,:,3]
    panels=[(name,composite(rgba,color)) for name,color in BACKGROUNDS]
    panels.append(('ALPHA',Image.fromarray(alpha,'L').convert('RGB')))
    edge=np.zeros((rgba.height,rgba.width,3),dtype=np.uint8)
    edge[alpha==255]=[235,235,235]
    edge[(alpha>0)&(alpha<255)]=[255,190,0]
    panels.append(('PARTIAL ALPHA',Image.fromarray(edge,'RGB')))
    label_h=28;gap=8;cols=3;rows=2
    sheet=Image.new('RGB',(cols*rgba.width+(cols+1)*gap,rows*(rgba.height+label_h)+(rows+1)*gap),(38,38,38))
    draw=ImageDraw.Draw(sheet)
    for i,(label,panel) in enumerate(panels):
        col=i%cols;row=i//cols;x=gap+col*(rgba.width+gap);y=gap+row*(rgba.height+label_h+gap)
        draw.text((x,y+6),label,fill=(255,255,255));sheet.paste(panel,(x,y+label_h))
    out_path.parent.mkdir(parents=True,exist_ok=True);sheet.save(out_path)
    report={'input':str(image_path),'output':str(out_path),'sourceSize':list(Image.open(image_path).size),
            'proofSize':list(sheet.size),'zoom':zoom,'transparentPixels':int((alpha==0).sum()),
            'partialAlphaPixels':int(((alpha>0)&(alpha<255)).sum()),'opaquePixels':int((alpha==255).sum()),
            'sha256':hashlib.sha256(image_path.read_bytes()).hexdigest()}
    print(json.dumps(report,ensure_ascii=False));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image');parser.add_argument('--out',required=True);parser.add_argument('--zoom',type=int,default=1)
    args=parser.parse_args();render(args.image,args.out,args.zoom)

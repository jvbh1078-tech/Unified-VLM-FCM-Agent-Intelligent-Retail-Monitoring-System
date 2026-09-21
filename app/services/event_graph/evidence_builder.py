from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw

def build_union_evidence(event_dir: Path, frame_rel: str, subject: dict, obj: dict) -> str | None:
    frame=event_dir/frame_rel
    if not frame.exists():
        return None
    try:
        img=Image.open(frame).convert("RGB")
        b1=subject["bbox"]; b2=obj["bbox"]; pad=30
        x1=max(0,min(b1[0],b2[0])-pad); y1=max(0,min(b1[1],b2[1])-pad)
        x2=min(img.width,max(b1[2],b2[2])+pad); y2=min(img.height,max(b1[3],b2[3])+pad)
        crop=img.crop((x1,y1,x2,y2)); dr=ImageDraw.Draw(crop)
        def l(b): return [b[0]-x1,b[1]-y1,b[2]-x1,b[3]-y1]
        dr.rectangle(l(b1), outline=(255,0,0), width=3)
        dr.rectangle(l(b2), outline=(0,160,255), width=3)
        try:
            dr.text((max(2,l(b1)[0]), max(2,l(b1)[1]-14)), str(subject.get("id", "subject")), fill=(255,0,0))
            dr.text((max(2,l(b2)[0]), max(16,l(b2)[1]-14)), str(obj.get("id", "object")), fill=(0,160,255))
        except Exception:
            pass
        rel=f"evidence/union/{subject['id']}__{obj['id']}.jpg"
        out=event_dir/rel; out.parent.mkdir(parents=True, exist_ok=True)
        crop.save(out, quality=90)
        return rel
    except Exception:
        return None

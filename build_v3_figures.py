#!/usr/bin/env python3
"""Versioned electrical schematic and logical timing for the finite V3 grammar."""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent / "results_v3"


def text(x, y, value, size=17):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="#233746">{escape(value)}</text>'


def line(points):
    return '<polyline points="' + ' '.join(f'{x},{y}' for x,y in points) + '" fill="none" stroke="#34576b" stroke-width="2"/>'


def node(x, y):
    return f'<circle cx="{x}" cy="{y}" r="4" fill="#34576b"/>'


def switch_h(x, y):
    return line([(x-30,y),(x-18,y)])+line([(x-18,y),(x+16,y-15)])+line([(x+18,y),(x+30,y)])


def switch_v(x, y):
    return line([(x,y-30),(x,y-18)])+line([(x,y-18),(x+15,y+16)])+line([(x,y+18),(x,y+30)])


def cap(x, y):
    return line([(x-7,y-20),(x-7,y+20)])+line([(x+7,y-20),(x+7,y+20)])


def save(name, width, height, items):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="{width}" height="{height}" fill="white"/><g font-family="Arial, sans-serif">'+''.join(items)+'</g></svg>'
    (OUT/name).write_text(svg)


def main():
    items = [text(45,42,"V3 source-anchored 6T2C",25),text(45,70,"Ideal SWT connection symbols",15),
             text(128,110,"VREF"),text(485,110,"VDD"),text(115,265,"G"),text(524,332,"S"),text(772,520,"X")]
    items += [line([(150,120),(150,130)]),switch_v(150,160),line([(150,190),(150,230),(430,230)]),
              text(185,155,"T_GREF"),text(185,180,"GC",14),
              line([(450,195),(450,265)]),line([(430,230),(450,230)]),
              line([(470,195),(470,265)]),line([(470,205),(500,205),(500,120)]),
              line([(470,255),(500,255),(500,420)]),text(540,218,"DTFT"),text(540,244,"IGZO"),
              line([(150,230),(150,600)]),line([(150,420),(273,420)]),cap(280,420),line([(287,420),(500,420)]),
              text(254,386,"CST"),line([(150,600),(273,600)]),cap(280,600),line([(287,600),(750,600)]),text(242,565,"CDATA"),
              line([(500,420),(585,420)]),switch_h(615,420),line([(645,420),(750,420),(750,600)]),
              text(560,375,"T_XANCHOR"),text(560,451,"XC: X to S",14),
              line([(500,420),(500,460)]),switch_v(500,490),line([(500,520),(500,540)]),
              text(535,490,"T_SCLAMP"),text(535,515,"SC",14),text(471,565,"VINIT"),
              line([(750,600),(790,600)]),switch_h(820,600),line([(850,600),(930,600)]),
              text(780,560,"T_DATA / DC"),text(886,633,"DATA"),
              line([(500,300),(670,300)]),switch_h(700,300),line([(730,300),(930,300),(930,380)]),
              text(665,267,"T_EM / EC"),text(962,356,"OLED_A"),
              line([(930,380),(930,400)]),
              '<path d="M910 400 L950 400 L930 430 Z M910 435 L950 435" fill="none" stroke="#34576b" stroke-width="2"/>',
              line([(930,435),(930,500)]),text(970,423,"OLED"),text(896,529,"ELVSS"),
              text(45,682,"A: XC = GC (4 controls)",16),text(500,682,"B: XC ON in PREP (5 controls)",16),
              text(45,712,"7T variants: see report.",16)]
    items += [node(x,y) for x,y in [(150,230),(150,420),(500,300),(500,420),(750,600)]]
    save("schematic.svg",1090,745,items)
    phases=["RESET","COMP","PREP","WRITE","EMIT"]
    wave=[("GC","11000"),("XC / A","11000"),("XC / B","11100"),("SC","10110"),("DC","00010"),("EC","00001")]
    items=[text(35,40,"V3 logical timing",24),text(530,40,"Phase view; not to scale",16)]
    for i,p in enumerate(phases):
        items.append(text(176+i*155,83,p,16))
    for j,(name,mask) in enumerate(wave):
        y=124+j*49
        items.append(text(35,y+9,name,16))
        points=[]
        for i,state in enumerate(mask):
            level=y-12 if state=="1" else y+12
            points.extend([(155+i*155,level),(155+(i+1)*155,level)])
        items.append(line(points))
    items += [text(35,449,"1 = SWT conducting",16),text(470,449,"Dead time: timings.csv",16),
              text(35,479,"COMP separated from WRITE",16),text(470,479,"DATA OFF before EM ON",16)]
    save("timing.svg",990,515,items)


if __name__ == "__main__":
    main()

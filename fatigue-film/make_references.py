"""Create the accompanying three-page, linked source and attribution PDF."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.utils import ImageReader
from PIL import Image

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'/'Fatigue_Failure_References.pdf'
pdfmetrics.registerFont(TTFont('Body',str(ROOT/'assets/fonts/DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('Bold',str(ROOT/'assets/fonts/DejaVuSans-Bold.ttf')))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold')
NAVY=HexColor('#0b1b2c'); TEAL=HexColor('#087a89'); GRAY=HexColor('#516475')
PW,PH=595.276,841.89
c=canvas.Canvas(str(OUT),pagesize=(PW,PH))
c.setTitle('Fatigue Failure - Sources, Image Credits and Scientific Notes')
c.setAuthor('Educational animation project')

LINKS={
 'fatigue':'https://ocw.mit.edu/courses/3-11-mechanics-of-materials-fall-1999/f678e01017186c53d45845ad93c07938_MIT3_11F99_fatigue.pdf',
 'sn':'https://ocw.mit.edu/courses/2-002-mechanics-and-materials-ii-spring-2004/db45866e2fc0cf164d96828936748e8f_lec21_notes.pdf',
 'fracture':'https://ocw.mit.edu/courses/3-11-mechanics-of-materials-fall-1999/e5bca953e1dbd0cd0376f0f77033dc0d_MIT3_11F99_frac.pdf',
 'nasa':'https://standards.nasa.gov/sites/default/files/standards/NASA/Revision/0/2023-12-14-NASA-HDBK-5010A-Vol-1-Rev-Approved.pdf',
 'nist':'https://www.nist.gov/image/semti-6al-4vpng-0',
 'nist_terms':'https://www.nist.gov/copyrights-disclaimers',
 'crank':'https://commons.wikimedia.org/wiki/File:0x-kurbel-def.jpg',
 'license':'https://creativecommons.org/licenses/by-sa/3.0/'
}


def para(s,x,y,width=507,size=10.5,color=GRAY,bold=False,leading=None):
    sty=ParagraphStyle('p',fontName='Bold' if bold else 'Body',fontSize=size,
                       leading=leading or size*1.46,textColor=color,alignment=TA_LEFT)
    p=Paragraph(s,sty)
    w,h=p.wrap(width,1000); p.drawOn(c,x,PH-y-h)
    return y+h


def heading(title,subtitle,num):
    c.setFillColor(NAVY); c.rect(0,PH-123,PW,123,fill=1,stroke=0)
    para('FATIGUE FAILURE',44,26,507,11,HexColor('#44d9df'),True)
    para(title,44,53,507,24,HexColor('#ffffff'),True,29)
    para(subtitle,44,91,507,9.5,HexColor('#c3d2df'))
    c.setStrokeColor(HexColor('#d5e0e8')); c.line(44,48,PW-44,48)
    para('3-minute teaching film | Source review: 30 October 2026',44,803,450,8,GRAY)
    para(str(num),532,802,20,9,TEAL,True)


def link(label,key,y):
    return para(f'<link href="{LINKS[key]}" color="#087a89"><u>{label}</u></link>',44,y,507,10)


def rule(y):
    c.setStrokeColor(HexColor('#d5e0e8')); c.line(44,PH-y,PW-44,PH-y)


heading('Research references','Sources for the concepts explained in the film',1)
y=153
entries=[
 ('01  Fatigue and crack growth',
  'Roylance, D. (2001). <b>Fatigue</b>. MIT, Department of Materials Science and Engineering.',
  'Used for repeated loading below yield, initiation and growth, fatigue-data scatter, and cyclic crack growth. See PDF pp. 1-4 and 6-7.',
  'MIT OpenCourseWare - Fatigue (PDF)','fatigue'),
 ('02  S-N curves and material differences',
  'Anand, L. and Parks, D. M. (2004). <b>Defect-Free Fatigue</b>. MIT 2.002 supplementary notes.',
  'Used for stress amplitude, logarithmic stress-life plots, and the distinction between steel endurance limits and aluminum-alloy trends. See PDF pp. 14 and 17-19.',
  'MIT OpenCourseWare - 2.002 lecture notes (PDF)','sn'),
 ('03  Stress intensity and fracture resistance',
  'Roylance, D. (2001). <b>Introduction to Fracture Mechanics</b>. MIT.',
  'Used for Mode I stress intensity, crack geometry and loading, toughness, and the limits of linear-elastic fracture mechanics.',
  'MIT OpenCourseWare - Introduction to Fracture Mechanics (PDF)','fracture'),
 ('04  Meaning and validity of K_Ic',
  'NASA (2023). <b>NASA-HDBK-5010, Volume 1, Revision A</b>: Fracture Control Implementation Handbook for Spaceflight Hardware.',
  'Used for the definition of linear-elastic, plane-strain fracture toughness and the need to satisfy validity conditions. See printed/PDF p. 25.',
  'NASA Standards - Fracture Control Implementation Handbook (PDF)','nasa')]
for title,citation,use,label,key in entries:
    y=para(title,44,y,507,13,TEAL,True)+7
    y=para(citation,44,y,507,10.5)+5
    y=para(use,44,y,507,10)+6
    y=link(label,key,y)+19
    if key!='nasa': rule(y-7)
c.showPage()

heading('Real photographs & credits','The scientific photographs are authentic; the motion diagrams are original schematics.',2)
para('05  Real fatigue-fractured titanium specimen',44,146,507,14,TEAL,True)
im=Image.open(ROOT/'assets/nist_specimen.png')
c.drawImage(ImageReader(im),44,PH-180-145,width=507,height=145,preserveAspectRatio=True,anchor='c',mask='auto')
y=para('<b>Credit:</b> National Institute of Standards and Technology (NIST). Uploaded 7 February 2017. SEM images of additive-manufactured Ti-6Al-4V fatigue fracture surfaces.',44,340,507,10)
y=para('The original white arrow identifies initiation at a lack-of-fusion defect. Black arrows indicate pores. Used at 00:23-00:33; resized with original arrows and scale bars retained.',44,y+6,507,10)
y=link('NIST image page and description','nist',y+7)
y=para(f'<link href="{LINKS["nist_terms"]}" color="#087a89"><u>NIST reuse policy</u></link>: unmarked site information may be copied with appropriate credit. No separate copyright restriction is shown on this image page.',44,y+6,507,9.5)
rule(y+17)
para('06  Real broken bicycle crank',44,y+35,507,14,TEAL,True)
photo_y=y+71
im=Image.open(ROOT/'assets/crank_fracture.jpg')
iw,ih=216,156
c.drawImage(ImageReader(im),44,PH-photo_y-ih,width=iw,height=ih,preserveAspectRatio=True,anchor='c',mask='auto')
py=para('<b>Photographer:</b> Oxensepp<br/><b>File:</b> 0x-kurbel-def.jpg<br/><b>Date:</b> 4 January 2014<br/><b>Source:</b> own work, Wikimedia Commons',280,photo_y,270,10)
py=para('Used at 02:31-02:40. The source description identifies slow fatigue growth and sudden fracture. The video resizes the image and adds explanatory arrows and labels.',280,py+9,270,10)
y2=max(photo_y+ih,py)+12
y2=link('Wikimedia Commons - original photograph, description and authorship','crank',y2)
y2=link('License: Creative Commons Attribution-ShareAlike 3.0 Unported','license',y2+5)
end=para('Attribution does not imply endorsement. The photograph and its annotated presentation retain the CC BY-SA 3.0 terms. Keep the credit and license when sharing.',44,y2+8,507,9.5)
assert end<787, ('photo page',end)
c.showPage()

heading('Illustrative data & production notes','How to interpret the numbers, drawings and timing',3)
y=para('The S-N numbers are invented teaching examples',44,149,507,15,TEAL,True)+13
y=para('No numerical S-N point, crack dimension, material toughness or service-life estimate is claimed to be a measurement of a bicycle crank. All scatter points are synthetic.',44,y,507,11)+18
rows=[('Example','Stress amplitude','Cycles to failure'),('Higher amplitude','300 MPa','10,000'),('Lower amplitude','180 MPa','1,000,000')]
xs=[44,229,397]; widths=[185,168,154]
for r,row in enumerate(rows):
    c.setFillColor(NAVY if r==0 else HexColor('#eef5f8'))
    c.rect(44,PH-y-36,507,36,fill=1,stroke=0)
    for j,s in enumerate(row): para(s,xs[j]+10,y+9,widths[j]-15,10,HexColor('#ffffff') if r==0 else GRAY,r==0)
    y+=37
y=para('The renderer uses S = 540 - 60 log10(N), with S in MPa, only over N = 10^3 to 10^7. It is a convenient illustrative curve, not a fitted material model. Comparisons assume the same material, mean stress, surface and environment.',44,y+12,507,10)+21
y=para('What the fracture animation assumes',44,y,507,15,TEAL,True)+11
y=para('K_I = Y * sigma * sqrt(pi * a). Y is the geometry factor; sigma is the applied tensile stress; a is the crack-length parameter. The paired animations hold Y constant: doubling stress doubles K_I, and increasing a by four doubles K_I. In real parts, Y can vary with crack geometry.',44,y,507,10.5)+12
y=para('K_I describes loading at a crack tip. K_Ic describes material resistance for a valid Mode I, linear-elastic, plane-strain test condition. Maximum K_I reaching K_Ic is the rapid-fracture criterion shown under those assumptions. A real crank may require another fracture-resistance measure if those assumptions fail.',44,y,507,10.5)+12
y=para('Fatigue growth can occur below K_Ic. Its rate also depends on the cyclic stress-intensity range, load ratio, environment and other conditions. K_Ic is not a fatigue-growth threshold.',44,y,507,10.5)+13
y=para('Exact schedule and reproducibility',44,y,507,15,TEAL,True)+10
y=para('<b>00:00-02:15:</b> concepts, including the title and outline (135 s, 75%).<br/><b>02:15-03:00:</b> bicycle application, care and source credits (45 s, 25%).<br/><b>Media:</b> 1920 x 1080, 24 fps, H.264 video and AAC English speech; English captions burned into the picture. A separate SRT is included.',44,y,507,10.5)+12
y=para('Source package: Python rendering and audio scripts, storyboard, real-photo assets, fonts and licenses, word timings, reusable narration, reference links, and the assignment prompt. Voice: en-US-AriaNeural via edge-tts. Bicycle art and diagrams are drawn by code.',44,y,507,9.5)+8
assert y<790, y
c.save()
print(OUT)


from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'architecture.png'
FONT = Path('C:/Windows/Fonts/malgun.ttf')
BOLD = Path('C:/Windows/Fonts/malgunbd.ttf')
im = Image.new('RGB', (1600, 1220), '#ffffff')
d = ImageDraw.Draw(im)
ink = '#142b46'
muted = '#516779'
blue = '#1767b2'


def font(size, bold=False):
    return ImageFont.truetype(str(BOLD if bold else FONT), size)


def label(x, y, text, size=24, color=ink, bold=False):
    d.text((x, y), text, font=font(size, bold), fill=color)


def center(x, y, text, size=24, color=ink, bold=False):
    f = font(size, bold)
    w = d.textlength(text, font=f)
    d.text((x - w / 2, y), text, font=f, fill=color)


def box(rect, fill, outline, width=3, radius=20):
    d.rounded_rectangle(rect, radius=radius, fill=fill, outline=outline, width=width)


def down_arrow(x, y1, y2):
    d.line((x, y1, x, y2 - 15), fill=blue, width=5)
    d.polygon([(x - 10, y2 - 17), (x + 10, y2 - 17), (x, y2)], fill=blue)


label(80, 35, 'AWS Web Service Architecture', 42, bold=True)
label(80, 96, 'Seoul  ap-northeast-2  |  Availability Zone  ap-northeast-2a', 23, muted)

box((470, 155, 1130, 270), '#f2f6fa', '#b2c3d1')
center(800, 170, 'Internet / Client', 30, bold=True)
center(800, 218, 'Browser: HTTP 80  |  Management: SSH 22', 22, muted)

box((80, 345, 1520, 1120), '#f8fbff', blue, width=4, radius=25)
label(115, 365, 'VPC  mission-vpc', 30, bold=True)
label(115, 412, '10.0.0.0/16', 24, blue)
label(115, 455, 'vpc-02fb9f982bc0efd7c', 19, muted)

down_arrow(800, 270, 430)
box((560, 430, 1040, 550), '#eaf2fc', blue)
center(800, 447, 'Internet Gateway  mission-igw', 25, bold=True)
center(800, 494, 'igw-0961d935789a435aa', 20, muted)

box((170, 620, 1430, 1060), '#eef7ff', '#73a8d7', width=3)
label(205, 638, 'Public Subnet  mission-public', 29, bold=True)
label(205, 683, '10.0.1.0/24  |  subnet-0afbc7e07dc484eb6', 20, muted)
d.line([(800, 550), (800, 590), (1000, 590)], fill=blue, width=5)
down_arrow(1000, 590, 740)

box((205, 760, 635, 995), '#ffffff', '#9ab5cf', width=2)
label(230, 779, 'Route Table', 25, bold=True)
label(230, 824, 'mission-public-rt', 22, blue)
label(230, 866, '0.0.0.0/0  ->  mission-igw', 21)
label(230, 907, '10.0.0.0/16  ->  local', 21, muted)
label(230, 949, 'Associated with mission-public', 18, muted)

box((700, 740, 1350, 1015), '#effaf5', '#36856d', width=3)
label(728, 755, 'Security Group  mission-web-sg', 24, '#23614e', True)
label(728, 796, 'HTTP 80: 0.0.0.0/0  |  SSH 22: 210.108.18.229/32', 19, '#23614e')
down_arrow(1000, 823, 843)
box((735, 845, 1315, 990), '#ffffff', '#36856d', width=2, radius=15)
label(759, 858, 'EC2  mission-web  |  t3.micro', 25, bold=True)
label(759, 899, 'Ubuntu / Nginx 1.24.0', 21)
label(759, 932, 'Public: 43.203.225.25  |  Private: 10.0.1.100', 19, muted)
label(759, 963, 'i-0eea7fc0ae794a282', 17, muted)

label(205, 1080, 'SG ID: sg-032fee0bca3d07fb8', 18, muted)
label(80, 1143, 'IAM cloud-lab: EC2 read access; listed write actions in Seoul; micro instance launches.', 21, muted)
label(80, 1180, 'Verified 2026-10-07: Nginx active | localhost 200 | outbound 200 | browser page displayed', 19, muted)

OUT.parent.mkdir(parents=True, exist_ok=True)
im.save(OUT)
print(OUT)

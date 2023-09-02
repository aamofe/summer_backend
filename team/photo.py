import pprint
import uuid
from PIL import Image, ImageDraw, ImageFont
import os
import tempfile
from summer_backend.settings import MEDIA_ROOT

from user.cos_utils import get_cos_client

def upload_cover_method( cover_id, url):
    client, bucket_name, bucket_region = get_cos_client()
    if cover_id == '' or cover_id == 0:
        cover_id = str(uuid.uuid4())
    ContentType = "image/png"
    cover_key = f"{url}/random_{cover_id}.png"
    with open(f"./random_{cover_id}.png",'rb') as fp:
        response_cover=client.put_object(
            Bucket=bucket_name,
            Body=fp,
            Key=cover_key,
            StorageClass='STANDARD',
            EnableMD5=False,
            ContentType=ContentType
        )
    if 'url' in response_cover:
        cover_url = response_cover['url']
    else:
        cover_url = f'https://{bucket_name}.cos.{bucket_region}.myqcloud.com/{cover_key}'
    return cover_url
def generate_cover(type, text, id):
    font_path =  os.path.join(MEDIA_ROOT,"msyh.ttc" )  # 请根据你的系统中的路径进行替换
    if type==1:
        font_size = 80  # 调整字体大小
        background_path = os.path.join(MEDIA_ROOT, 'background.png')  # 请替换为你的背景图片路径
        image_width, image_height = 1132, 576
        background = Image.open(background_path)
        if '\u4e00' <= text[0] <= '\u9fff':
            text = ' '.join([text[i:i + 1] for i in range(0, len(text))])
    elif type==3:
        font_size =250
        image_width, image_height = 960,960
        background = Image.new("RGBA", (image_width, image_height), (62,109,186, 255))
    else:
        font_size = 750 # 调整字体大小
        image_width, image_height = 960,960
        background = Image.new("RGBA", (image_width, image_height), (62,109,186, 255))
        text=text[0]
    font = ImageFont.truetype(font_path, font_size)
    draw = ImageDraw.Draw(background)
    if type == 1:  # 项目封面
        url='project_cover'
        while font.getlength(text) > 580:
            text = text[:-1]
        # x_start = (387 - font.getlength(text))
        x_start = 380 - font.getlength(text) / 2
        y_start = 330
        text_color = "#2a48a2"#蓝色
        font = ImageFont.truetype(font_path, font_size)
        draw.text((x_start, y_start), text, font=font, fill=text_color)
    elif type==3:
        url='group_cover'
        letter=text.split('、')
        text_color = "#FFFFFF"
        font = ImageFont.truetype(font_path, font_size)
        length=len(letter)
        circle = 1 if length < 4 else (2 if length < 7 else 3)
        if length==4:
            y=[160,480]
            x=[160,480]
            for i in range(2):
                for j in range(2):
                    draw.text((x[j], y[i]), letter[2 * i+j], font=font, fill=text_color)
        else:
            for i in range(circle):
                ll=min(3,length-3*i)
                y = [320] if length < 4 else ([160, 480] if length < 7 else [0, 320, 640])
                x = [320] if ll == 1 else ([160, 480] if ll == 2 else [0, 320, 640])
                for j in range(ll):
                    draw.text((x[j], y[i]), letter[3 * i+j], font=font, fill=text_color)

    else:  # 团队封面
        url='team_cover'
        while font.getlength(text) > 960:
            text = text[:-1]
        x_start = (image_width - font.getlength(text)) // 2
        y_start = -2
        text_color = "#FFFFFF"  # 白色文字
        font = ImageFont.truetype(font_path, font_size)
        draw.text((x_start, y_start), text, font=font, fill=text_color)

    # 创建临时文件并将图像保存在其中
    output_path = f"./random_{id}.png"
    background.save(output_path, format="png")
    background.show()
    background.close()
    url=upload_cover_method(id,url)
    os.remove(output_path)
    print("generate_method : ",url)
    return url

# user_names_list=['ni','你好','什么','aaya ','希望','啊啊啊啊','什么是是是是','我不开思南县啊啊啊','uidsnd','后打开打开']
# first_characters = [name[0] for name in user_names_list]
# text = "、".join(first_characters)
# generate_cover(3,text,2)
import pprint
import uuid
from PIL import Image, ImageDraw, ImageFont
import os
import tempfile

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
    font_path = "../static/font/msyh.ttc"  # 请根据你的系统中的路径进行替换



    if type==1:
        font_size = 80  # 调整字体大小
        background_path = "../static/img/background.png"  # 请替换为你的背景图片路径
        image_width, image_height = 1132, 576
        background = Image.open(background_path)
        if '\u4e00' <= text[0] <= '\u9fff':
            text = ' '.join([text[i:i + 1] for i in range(0, len(text))])

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
    # background.show()
    background.close()
    url=upload_cover_method(id,url)
    os.remove(output_path)
    print(url)
    return url
# for i in range(1,6):

# id_list=[1,5,6,7,8,9,10,15,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36]
#
# text_list=['傻逼之家','aaaaaaa','a2','缅北分部3群','缅北分部4群','哈哈哈哈哈','呜呜呜呜'
#            '傻逼之家 (Copy)','傻逼之家 (Copy)','新建项目1','新建项目2','新建项目3',
#            '缅北分部4群','缅北分部4群','缅北分部4群','缅北分部4群','缅北分部4群','缅北分部4群',
#            '傻逼之家 (Copy)','缅北分部4群','傻逼之家 (Copy)','傻逼之家 (Copy)','傻逼之家 (Copy)',
#            '缅北分部4群 (Copy)','缅北分部4群 (Copy) (Copy)','bbbbbbb','ll'
# ]
#
# for i in range(27):
generate_cover(1,"ll",36)
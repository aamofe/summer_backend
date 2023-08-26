from PIL import Image, ImageDraw, ImageFont
import os
import tempfile

def generate_temporary_image(text, font_path, font_size, x_start, y_start, image_width, image_height):
    temp_image = Image.new("RGBA", (image_width, image_height), (0, 0, 255, 255))
    draw = ImageDraw.Draw(temp_image)

    font = ImageFont.truetype(font_path, font_size)
    text_color = "#ffffff"
    draw.text((x_start, y_start), text, font=font, fill=text_color)

    # 创建临时文件并将图像保存在其中
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    temp_image.save(temp_file, format="PNG")
    temp_file.close()

    return temp_file.name,temp_file

def generate_cover(type, text, id):
    background_path = "../static/img/background.png"  # 请替换为你的背景图片路径
    background = Image.open(background_path)
    image_width, image_height = background.size

    font_path = "../static/font/msyh.ttc"  # 请根据你的系统中的路径进行替换
    font_size = 80  # 调整字体大小

    x_start = 0
    y_start = 0
    text_width = 0
    text_height = 0

    if '\u4e00' <= text[0] <= '\u9fff':
        text = ' '.join([text[i:i + 1] for i in range(0, len(text))])

    font = ImageFont.truetype(font_path, font_size)
    draw = ImageDraw.Draw(background)
    text_color=""
    if type == 1:  # 项目封面
        x_start = (image_width - font.getlength(text)) // 2
        y_start = 330
        text_color = "#2a48a2"
        while font.getlength(text) > 580:
            text = text[:-1]
    elif type == 2:  # 团队封面
        x_start = (image_width - font.getlength(text)) // 2
        y_start = (image_height - font.getsize(text)[1]) // 2
        text_color = "#ffffff"  # 白色文字
    else:#原型封面
        x_start = (image_width - font.getlength(text)) // 2
        y_start = (image_height - font.getsize(text)[1]) // 2
        text_color = "#ffffff"  # 白色文字

    draw.text((x_start, y_start), text, font=font, fill=text_color)

    temp_image_path,temp_image = generate_temporary_image(text, font_path, font_size, x_start, y_start, image_width,image_height)
    return temp_image_path,temp_image


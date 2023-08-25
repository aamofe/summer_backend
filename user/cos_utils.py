import os

from qcloud_cos import CosConfig, CosS3Client


def get_cos_client():

    secret_id = 'AKIDOk2PhswtjUCpMm6JP1Z5Sju0sfL5kIj7'     # 用户的 SecretId
    secret_key = 'Vq6HsNm5IRp6LBzhImBWp8Sjx6A83vje'   # 用户的 SecretKey
    bucket_name = 'summer-1315620690'
    region = 'ap-beijing'                       # COS桶所属的地域
    token = None                                # 如果使用临时密钥，填写对应的token，否则为None
    scheme = 'https'                            # 访问协议，https或http

    config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
    client = CosS3Client(config)
    return client, bucket_name, region


#啥东西都往里放

Label = {
'Politics': '政治',
'Porn': '色情',
'Ads': '广告',
'Terrorism': '暴恐'
}

Category = {
'ChinaMap': '中国地图',
'ForeignLeaders': '外国/地区领导人',
'Gallery': '违规图库',
'NegativeFigure': '负面人物',
'NegativeFlagsLogos': '负面旗帜&标识',
'PositiveCharacter': '正面人物',
'PositiveFlagsLogos': '正面旗帜&标识',
'Underdog': '劣迹艺人',
'ObsceneBehaviour': '性暗示/低俗行为',
'SexProducts': '性用品相关',
'Sexy': '性感内容',
'Sexuality': '性器官裸露/性行为',
'LOGO': 'LOGO检测识别',
'QRCode': '二维码/条形码识别',
'BloodyScenes': '血腥场景',
'ColdWeapons': '刀剑等冷兵器',
'CrowdGathering': '人群聚集',
'Firearms': '枪支等热武器',
'FireExplosion': '火灾/爆炸场景',
'LargeWeapons': '大型军事武器',
'SpecialDress': '特殊着装',
'TerrorismActs': '暴力恐怖行为',
'Uniforms': '军警制服'
}

SubLabel = {
'SM': 'SM',
'ACGPorn': 'ACG色情',
'NakedAnimal': '动物裸露',
'SexAids': '性用品',
'NakedArt': '裸露艺术品',
'WomenSexy': '女性性感着装',
'MenSexy': '男性性感着装',
'WomenSexyBack': '女性性感-背部',
'WomenSexyChest': '女性性感-胸部',
'WomenSexyLeg': '女性性感-腿部',
'ACGSexy': 'ACG性感',
'SexySimilar': '性感画面',
'HipCloseUp': '臀部性感',
'FootCloseUp': '足部特写',
'SexyBehavior': '性行为',
'WomenPrivatePart': '女性下体',
'WomenChest': '女性胸部',
'MenPrivatePart': '男性下体',
'ButtocksExposed': '臀部',
'NakedChild': '儿童裸露',
'PornSimilar': '色情画面',
'AppLogo': '互联网应用台标',
'MovieLogo': '电影台标',
'CCTVLogo': '央视台标',
'LocalTVLogo': '地方卫视台标',
'QRCODE': '二维码',
'Blood': '血腥画面',
'Knife': '刀等冷兵器',
}
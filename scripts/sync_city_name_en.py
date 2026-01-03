# -*- coding: utf-8 -*-
"""
同步 city_name_en 字段
优先级：
1. 如果 city_name 是英文，直接使用
2. 从 airport_name_en 提取城市名（移除 Airport 等后缀）
3. 使用翻译映射表
运行方式：python scripts/sync_city_name_en.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from App_new import create_app
from App_new.exts import db
from App_new.business.flight.models.models import AirportData


def extract_city_from_airport_name(airport_name_en):
    """从机场英文名提取城市名"""
    if not airport_name_en:
        return None

    name = airport_name_en.strip()

    # 移除常见后缀
    suffixes = [
        ' International Airport', ' Intl Airport', ' Int\'l Airport',
        ' Domestic Airport', ' Regional Airport', ' Metropolitan Airport',
        ' Airport', ' Airfield', ' Aerodrome',
        # 中国机场特有后缀
        ' Changi', ' Capital', ' Pudong', ' Hongqiao', ' Baiyun', ' Bao\'an',
        ' Shuangliu', ' Tianfu', ' Daxing', ' Xiaoshan', ' Lukou', ' Xinzheng',
        ' Zhengding', ' Longjia', ' Taoxian', ' Zhoushuizi', ' Liuting',
        ' Yaoqiang', ' Binhai', ' Gaoqi', ' Changshui', ' Jiangbei',
        ' Huanghua', ' Meilan', ' Fenghuang', ' Longdongbao', ' Gonggar',
        ' Diwopu', ' Taiping', ' Wusu', ' Caojiapu',
    ]

    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
            break

    # 移除括号内容 如 "Beijing (Peking)"
    name = re.sub(r'\s*\([^)]*\)', '', name).strip()

    # 如果结果合理（长度>1且不等于原名），返回
    if name and len(name) > 1:
        return name

    return None


# 中文城市名到英文的翻译映射（备用）
CITY_TRANSLATION = {
    # 中国大陆
    '北京': 'Beijing', '上海': 'Shanghai', '广州': 'Guangzhou', '深圳': 'Shenzhen',
    '成都': 'Chengdu', '重庆': 'Chongqing', '武汉': 'Wuhan', '西安': 'Xian',
    '杭州': 'Hangzhou', '南京': 'Nanjing', '昆明': 'Kunming', '厦门': 'Xiamen',
    '青岛': 'Qingdao', '大连': 'Dalian', '天津': 'Tianjin', '沈阳': 'Shenyang',
    '长沙': 'Changsha', '郑州': 'Zhengzhou', '海口': 'Haikou', '三亚': 'Sanya',
    '福州': 'Fuzhou', '南宁': 'Nanning', '贵阳': 'Guiyang', '拉萨': 'Lhasa',
    '乌鲁木齐': 'Urumqi', '哈尔滨': 'Harbin', '长春': 'Changchun', '济南': 'Jinan',
    '石家庄': 'Shijiazhuang', '太原': 'Taiyuan', '呼和浩特': 'Hohhot', '银川': 'Yinchuan',
    '兰州': 'Lanzhou', '西宁': 'Xining', '珠海': 'Zhuhai', '汕头': 'Shantou',
    '温州': 'Wenzhou', '宁波': 'Ningbo', '烟台': 'Yantai', '无锡': 'Wuxi',
    '合肥': 'Hefei', '南昌': 'Nanchang', '洛阳': 'Luoyang', '桂林': 'Guilin',
    '丽江': 'Lijiang', '大理': 'Dali', '西双版纳': 'Xishuangbanna', '张家界': 'Zhangjiajie',
    '黄山': 'Huangshan', '九寨沟': 'Jiuzhaigou', '敦煌': 'Dunhuang', '威海': 'Weihai',
    '常州': 'Changzhou', '徐州': 'Xuzhou', '扬州': 'Yangzhou', '苏州': 'Suzhou',
    '泉州': 'Quanzhou', '惠州': 'Huizhou', '中山': 'Zhongshan', '东莞': 'Dongguan',
    '佛山': 'Foshan', '江门': 'Jiangmen', '湛江': 'Zhanjiang', '北海': 'Beihai',
    '柳州': 'Liuzhou', '遵义': 'Zunyi', '绵阳': 'Mianyang', '宜宾': 'Yibin',
    '泸州': 'Luzhou', '攀枝花': 'Panzhihua', '西昌': 'Xichang', '九江': 'Jiujiang',
    '赣州': 'Ganzhou', '景德镇': 'Jingdezhen', '宜昌': 'Yichang', '襄阳': 'Xiangyang',
    '荆州': 'Jingzhou', '恩施': 'Enshi', '岳阳': 'Yueyang', '常德': 'Changde',
    '衡阳': 'Hengyang', '株洲': 'Zhuzhou', '湘潭': 'Xiangtan', '怀化': 'Huaihua',
    '延安': 'Yanan', '榆林': 'Yulin', '汉中': 'Hanzhong', '安康': 'Ankang',
    '酒泉': 'Jiuquan', '嘉峪关': 'Jiayuguan', '天水': 'Tianshui', '张掖': 'Zhangye',
    '包头': 'Baotou', '赤峰': 'Chifeng', '鄂尔多斯': 'Ordos', '通辽': 'Tongliao',
    '吉林': 'Jilin', '延吉': 'Yanji', '牡丹江': 'Mudanjiang', '佳木斯': 'Jiamusi',
    '齐齐哈尔': 'Qiqihar', '大庆': 'Daqing', '伊春': 'Yichun', '漠河': 'Mohe',
    '满洲里': 'Manzhouli', '海拉尔': 'Hailar', '锡林浩特': 'Xilinhot', '二连浩特': 'Erenhot',
    '阿勒泰': 'Altay', '喀什': 'Kashgar', '和田': 'Hotan', '库尔勒': 'Korla',
    '伊宁': 'Yining', '阿克苏': 'Aksu', '吐鲁番': 'Turpan', '哈密': 'Hami',
    '克拉玛依': 'Karamay', '石河子': 'Shihezi', '博乐': 'Bole', '塔城': 'Tacheng',
    '日喀则': 'Shigatse', '林芝': 'Nyingchi', '昌都': 'Chamdo', '阿里': 'Ngari',
    '格尔木': 'Golmud', '玉树': 'Yushu', '德令哈': 'Delingha',

    # 港澳台
    '香港': 'Hong Kong', '澳门': 'Macau', '台北': 'Taipei', '高雄': 'Kaohsiung',
    '台中': 'Taichung', '台南': 'Tainan', '花莲': 'Hualien', '台东': 'Taitung',
    '澎湖': 'Penghu', '金门': 'Kinmen', '马祖': 'Matsu',

    # 日本
    '东京': 'Tokyo', '大阪': 'Osaka', '名古屋': 'Nagoya', '札幌': 'Sapporo',
    '福冈': 'Fukuoka', '冲绳': 'Okinawa', '那霸': 'Naha', '京都': 'Kyoto',
    '神户': 'Kobe', '广岛': 'Hiroshima', '仙台': 'Sendai', '新�的': 'Niigata',
    '长崎': 'Nagasaki', '�的�的': 'Kagoshima', '熊本': 'Kumamoto', '静冈': 'Shizuoka',
    '金�的': 'Kanazawa', '小松': 'Komatsu', '富山': 'Toyama', '松山': 'Matsuyama',
    '高松': 'Takamatsu', '�的�的': 'Okayama', '旭川': 'Asahikawa', '函馆': 'Hakodate',
    '�的的': 'Kushiro', '带广': 'Obihiro', '青森': 'Aomori', '秋田': 'Akita',
    '山形': 'Yamagata', '福岛': 'Fukushima', '�的的': 'Miyazaki',

    # 韩国
    '首尔': 'Seoul', '釜山': 'Busan', '济州': 'Jeju', '仁川': 'Incheon',
    '大邱': 'Daegu', '光州': 'Gwangju', '清州': 'Cheongju', '襄阳': 'Yangyang',
    '务安': 'Muan', '蔚山': 'Ulsan', '原州': 'Wonju',

    # 东南亚
    '新加坡': 'Singapore', '吉隆坡': 'Kuala Lumpur', '槟城': 'Penang',
    '沙巴': 'Kota Kinabalu', '亚庇': 'Kota Kinabalu', '古晋': 'Kuching',
    '兰卡威': 'Langkawi', '新山': 'Johor Bahru', '马六甲': 'Malacca',
    '曼谷': 'Bangkok', '清迈': 'Chiang Mai', '普吉': 'Phuket', '苏梅': 'Koh Samui',
    '甲米': 'Krabi', '芭提雅': 'Pattaya', '清莱': 'Chiang Rai', '合艾': 'Hat Yai',
    '胡志明': 'Ho Chi Minh', '河内': 'Hanoi', '岘港': 'Da Nang', '芽庄': 'Nha Trang',
    '富国': 'Phu Quoc', '顺化': 'Hue', '海防': 'Hai Phong', '大叻': 'Da Lat',
    '马尼拉': 'Manila', '宿务': 'Cebu', '长滩': 'Boracay', '达沃': 'Davao',
    '克拉克': 'Clark', '卡利博': 'Kalibo', '公主港': 'Puerto Princesa',
    '雅加达': 'Jakarta', '巴厘岛': 'Bali', '登巴萨': 'Denpasar', '泗水': 'Surabaya',
    '日惹': 'Yogyakarta', '棉兰': 'Medan', '万隆': 'Bandung', '龙目': 'Lombok',
    '仰光': 'Yangon', '曼德勒': 'Mandalay', '蒲甘': 'Bagan', '内比都': 'Naypyidaw',
    '暹粒': 'Siem Reap', '金边': 'Phnom Penh', '西哈努克': 'Sihanoukville',
    '万象': 'Vientiane', '琅勃拉邦': 'Luang Prabang', '巴色': 'Pakse',
    '斯里巴加湾': 'Bandar Seri Begawan', '文莱': 'Brunei',
    '帝力': 'Dili',

    # 南亚
    '德里': 'Delhi', '新德里': 'New Delhi', '孟买': 'Mumbai', '金奈': 'Chennai',
    '班加罗尔': 'Bangalore', '加尔各答': 'Kolkata', '海德拉巴': 'Hyderabad',
    '艾哈迈达巴德': 'Ahmedabad', '浦那': 'Pune', '果阿': 'Goa', '斋浦尔': 'Jaipur',
    '科伦坡': 'Colombo', '马累': 'Male', '马尔代夫': 'Maldives',
    '加德满都': 'Kathmandu', '达卡': 'Dhaka', '吉大港': 'Chittagong',
    '卡拉奇': 'Karachi', '伊斯兰堡': 'Islamabad', '拉合尔': 'Lahore',

    # 中东
    '迪拜': 'Dubai', '阿布扎比': 'Abu Dhabi', '多哈': 'Doha', '巴林': 'Bahrain',
    '科威特': 'Kuwait', '马斯喀特': 'Muscat', '利雅得': 'Riyadh', '吉达': 'Jeddah',
    '麦加': 'Mecca', '麦地那': 'Medina', '特拉维夫': 'Tel Aviv', '安曼': 'Amman',
    '贝鲁特': 'Beirut', '开罗': 'Cairo', '伊斯坦布尔': 'Istanbul', '安卡拉': 'Ankara',
    '德黑兰': 'Tehran', '巴格达': 'Baghdad', '大马士革': 'Damascus',
    '耶路撒冷': 'Jerusalem', '亚历山大': 'Alexandria', '沙姆沙伊赫': 'Sharm El Sheikh',
    '卢克索': 'Luxor', '阿斯旺': 'Aswan', '赫尔格达': 'Hurghada',

    # 澳洲/新西兰
    '悉尼': 'Sydney', '墨尔本': 'Melbourne', '布里斯班': 'Brisbane', '珀斯': 'Perth',
    '阿德莱德': 'Adelaide', '凯恩斯': 'Cairns', '黄金海岸': 'Gold Coast',
    '堪培拉': 'Canberra', '达尔文': 'Darwin', '霍巴特': 'Hobart',
    '奥克兰': 'Auckland', '基督城': 'Christchurch', '惠灵顿': 'Wellington',
    '皇后镇': 'Queenstown', '但尼丁': 'Dunedin', '罗托鲁瓦': 'Rotorua',

    # 北美
    '洛杉矶': 'Los Angeles', '旧金山': 'San Francisco', '纽约': 'New York',
    '芝加哥': 'Chicago', '达拉斯': 'Dallas', '亚特兰大': 'Atlanta',
    '迈阿密': 'Miami', '西雅图': 'Seattle', '波士顿': 'Boston', '丹佛': 'Denver',
    '拉斯维加斯': 'Las Vegas', '凤凰城': 'Phoenix', '华盛顿': 'Washington',
    '费城': 'Philadelphia', '圣地亚哥': 'San Diego', '休斯顿': 'Houston',
    '火奴鲁鲁': 'Honolulu', '檀香山': 'Honolulu', '夏威夷': 'Hawaii',
    '温哥华': 'Vancouver', '多伦多': 'Toronto', '蒙特利尔': 'Montreal',
    '卡尔加里': 'Calgary', '渥太华': 'Ottawa', '埃德蒙顿': 'Edmonton',
    '墨西哥城': 'Mexico City', '坎昆': 'Cancun', '瓜达拉哈拉': 'Guadalajara',

    # 欧洲
    '伦敦': 'London', '巴黎': 'Paris', '法兰克福': 'Frankfurt', '慕尼黑': 'Munich',
    '阿姆斯特丹': 'Amsterdam', '布鲁塞尔': 'Brussels', '苏黎世': 'Zurich',
    '日内瓦': 'Geneva', '维也纳': 'Vienna', '布拉格': 'Prague', '华沙': 'Warsaw',
    '布达佩斯': 'Budapest', '罗马': 'Rome', '米兰': 'Milan', '威尼斯': 'Venice',
    '佛罗伦萨': 'Florence', '那不勒斯': 'Naples', '马德里': 'Madrid',
    '巴塞罗那': 'Barcelona', '里斯本': 'Lisbon', '雅典': 'Athens',
    '哥本哈根': 'Copenhagen', '斯德哥尔摩': 'Stockholm', '奥斯陆': 'Oslo',
    '赫尔辛基': 'Helsinki', '都柏林': 'Dublin', '爱丁堡': 'Edinburgh',
    '曼彻斯特': 'Manchester', '伯明翰': 'Birmingham', '格拉斯哥': 'Glasgow',
    '莫斯科': 'Moscow', '圣彼得堡': 'St Petersburg', '柏林': 'Berlin',
    '汉堡': 'Hamburg', '杜塞尔多夫': 'Dusseldorf', '科隆': 'Cologne',
    '斯图加特': 'Stuttgart', '纽伦堡': 'Nuremberg', '尼斯': 'Nice',
    '里昂': 'Lyon', '马赛': 'Marseille', '波尔多': 'Bordeaux', '图卢兹': 'Toulouse',
    '巴塞尔': 'Basel', '伯尔尼': 'Bern', '萨尔茨堡': 'Salzburg', '因斯布鲁克': 'Innsbruck',
    '布拉迪斯拉发': 'Bratislava', '卢布尔雅那': 'Ljubljana', '萨格勒布': 'Zagreb',
    '贝尔格莱德': 'Belgrade', '索非亚': 'Sofia', '布加勒斯特': 'Bucharest',
    '基辅': 'Kyiv', '明斯克': 'Minsk', '里加': 'Riga', '塔林': 'Tallinn',
    '维尔纽斯': 'Vilnius', '克拉科夫': 'Krakow', '格但斯克': 'Gdansk',
    '雷克雅未克': 'Reykjavik', '卑尔根': 'Bergen', '哥德堡': 'Gothenburg',
    '马尔默': 'Malmo', '奥胡斯': 'Aarhus', '圣托里尼': 'Santorini',
    '米科诺斯': 'Mykonos', '克里特': 'Crete', '伊拉克利翁': 'Heraklion',
    '塞萨洛尼基': 'Thessaloniki', '波尔图': 'Porto', '塞维利亚': 'Seville',
    '瓦伦西亚': 'Valencia', '马拉加': 'Malaga', '毕尔巴鄂': 'Bilbao',
    '帕尔马': 'Palma de Mallorca', '伊维萨': 'Ibiza', '特内里费': 'Tenerife',
    '大加那利': 'Gran Canaria', '摩纳哥': 'Monaco', '卢森堡': 'Luxembourg',

    # 非洲
    '约翰内斯堡': 'Johannesburg', '开普敦': 'Cape Town', '德班': 'Durban',
    '内罗毕': 'Nairobi', '亚的斯亚贝巴': 'Addis Ababa', '卡萨布兰卡': 'Casablanca',
    '马拉喀什': 'Marrakech', '阿尔及尔': 'Algiers', '突尼斯': 'Tunis',
    '拉各斯': 'Lagos', '阿布贾': 'Abuja', '阿克拉': 'Accra', '达喀尔': 'Dakar',
    '亚历山大港': 'Alexandria', '毛里求斯': 'Mauritius', '塞舌尔': 'Seychelles',
    '桑给巴尔': 'Zanzibar', '坦噶': 'Tanga', '达累斯萨拉姆': 'Dar es Salaam',
    '维多利亚瀑布': 'Victoria Falls', '温得和克': 'Windhoek', '哈拉雷': 'Harare',
    '路易港': 'Port Louis', '维多利亚': 'Victoria',

    # 南美
    '圣保罗': 'Sao Paulo', '里约热内卢': 'Rio de Janeiro', '布宜诺斯艾利斯': 'Buenos Aires',
    '圣地亚哥': 'Santiago', '利马': 'Lima', '波哥大': 'Bogota', '加拉加斯': 'Caracas',
    '基多': 'Quito', '蒙得维的亚': 'Montevideo', '亚松森': 'Asuncion',
    '拉巴斯': 'La Paz', '库斯科': 'Cusco', '马丘比丘': 'Machu Picchu',
    '伊瓜苏': 'Iguazu', '巴西利亚': 'Brasilia', '萨尔瓦多': 'Salvador',
    '累西腓': 'Recife', '福塔雷萨': 'Fortaleza', '马瑙斯': 'Manaus',
    '麦德林': 'Medellin', '卡塔赫纳': 'Cartagena',
}


def is_chinese(text):
    """判断字符串是否包含中文字符"""
    if not text:
        return False
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False


def translate_city_name(city_name):
    """翻译城市名"""
    if not city_name:
        return None

    city_name = city_name.strip()

    # 如果已经是英文，直接返回
    if not is_chinese(city_name):
        return city_name

    # 查找翻译映射
    if city_name in CITY_TRANSLATION:
        return CITY_TRANSLATION[city_name]

    # 尝试部分匹配（去掉"市"、"省"等后缀）
    for suffix in ['市', '省', '县', '区', '岛']:
        if city_name.endswith(suffix):
            base_name = city_name[:-1]
            if base_name in CITY_TRANSLATION:
                return CITY_TRANSLATION[base_name]

    return None


app = create_app()

with app.app_context():
    airports = AirportData.query.all()

    updated = 0
    skipped = 0
    failed = []

    for airport in airports:
        # 如果已有 city_name_en，跳过
        if airport.city_name_en:
            skipped += 1
            continue

        city_en = None
        source = ''

        # 优先级1: 如果 city_name 是英文，直接使用
        if airport.city_name and not is_chinese(airport.city_name):
            city_en = airport.city_name.strip()
            source = 'city_name(英文)'

        # 优先级2: 从 airport_name_en 提取城市名
        if not city_en and airport.airport_name_en:
            city_en = extract_city_from_airport_name(airport.airport_name_en)
            if city_en:
                source = 'airport_name_en'

        # 优先级3: 使用翻译映射表
        if not city_en and airport.city_name:
            city_en = translate_city_name(airport.city_name)
            if city_en:
                source = '翻译映射'

        if city_en:
            airport.city_name_en = city_en
            updated += 1
            print(f"[OK] {airport.airport_IATA}: {airport.city_name} -> {city_en} ({source})")
        else:
            failed.append((airport.airport_IATA, airport.city_name, airport.airport_name_en))
            print(f"[FAIL] {airport.airport_IATA}: {airport.city_name}")

    db.session.commit()

    print(f"\n===== 同步完成 =====")
    print(f"更新: {updated}")
    print(f"跳过(已有): {skipped}")
    print(f"失败: {len(failed)}")

    if failed:
        print(f"\n未处理的机场:")
        for iata, city, airport_en in failed:
            print(f"  {iata}: city_name={city}, airport_name_en={airport_en}")

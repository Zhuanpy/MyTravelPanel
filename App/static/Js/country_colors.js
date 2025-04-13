const countryColors = {
    '日本': {
        border: '#FF6B6B',
        gradient: 'linear-gradient(135deg, #FF6B6B, #FF8787)',
        bg: '#FFF5F5',
        icon: 'fa-sun',
        region: 'east-asia'
    },
    '韩国': {
        border: '#4ECDC4',
        gradient: 'linear-gradient(135deg, #4ECDC4, #45B7AF)',
        bg: '#F5FFFE',
        icon: 'fa-star',
        region: 'east-asia'
    },
    '泰国': {
        border: '#FFD93D',
        gradient: 'linear-gradient(135deg, #FFD93D, #FFC107)',
        bg: '#FFF9E6',
        icon: 'fa-palm-tree',
        region: 'southeast-asia'
    },
    // 东南亚国家组
    ...Object.fromEntries([
        ['越南', ['#95A5A6', '#7F8C8D', '#F5F6F7', 'fa-motorcycle']],
        ['马来西亚', ['#6C5CE7', '#5B4BC4', '#F5F3FF', 'fa-mosque']],
        ['新加坡', ['#00B894', '#00A187', '#F5FFFB', 'fa-city']],
        ['印度尼西亚', ['#FF7675', '#FF6B6B', '#FFF5F5', 'fa-volcano']],
        ['菲律宾', ['#74B9FF', '#6C5CE7', '#F5F9FF', 'fa-water']],
        ['柬埔寨', ['#FDCB6E', '#FFD93D', '#FFF9E6', 'fa-temple']],
        ['老挝', ['#A8E6CF', '#00B894', '#F5FFFB', 'fa-mountain']],
        ['缅甸', ['#FFA502', '#FFD93D', '#FFF9E6', 'fa-pagoda']],
        ['文莱', ['#81ECEC', '#00CEC9', '#F5FFFF', 'fa-oil-well']],
        ['东帝汶', ['#FF7675', '#FF6B6B', '#FFF5F5', 'fa-island-tropical']]
    ].map(([country, [color1, color2, bg, icon]]) => [
        country,
        {
            border: color1,
            gradient: `linear-gradient(135deg, ${color1}, ${color2})`,
            bg: bg,
            icon: icon,
            region: 'southeast-asia'
        }
    ])),
    default: {
        border: '#9F7AEA',
        gradient: 'linear-gradient(135deg, #9F7AEA, #805AD5)',
        bg: '#F5F3FF',
        icon: 'fa-globe-asia',
        region: 'other'
    }
}; 
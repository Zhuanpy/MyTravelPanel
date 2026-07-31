"""旅游项目状态诊断 / 修复

用途:
  1. 排查"复制的项目不出现在项目列表里"——列表按 project_status 精确筛选，
     状态为空字符串、NULL 或不在下拉选项里的项目在任何标签下都看不到。
  2. 排查"更新项目失败: Column 'project_status' cannot be null"——
     编辑弹窗的下拉框回填不上库里的值时，该字段不会被提交，后端就写成了 NULL。

运行方式:
    python scripts/tools/20260731_diagnose_tour_project_status.py            # 只读，看全表状态分布
    python scripts/tools/20260731_diagnose_tour_project_status.py --id 83    # 看单个项目明细
    python scripts/tools/20260731_diagnose_tour_project_status.py --fix      # 把非法状态统一改成"处理中"
    python scripts/tools/20260731_diagnose_tour_project_status.py --fix --to 待出行 --id 83
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from App_new import create_app
from App_new.exts import db
from App_new.business.tour.models.TourProject import TourProject, TourGroup

# 项目状态的合法取值（与创建页 / 列表筛选 / 编辑弹窗的下拉选项保持一致）
VALID_STATUS = ['处理中', '待出行', '已完成', '忽略单']


def show(value):
    """把 None / 空串 / 带空格的值显示清楚"""
    if value is None:
        return '<NULL>'
    return '[%s]' % value


def dump_project(p):
    print('  id=%s  %s' % (p.id, p.project_name))
    print('     project_status : %s  %s' % (show(p.project_status),
                                            '✅ 合法' if p.project_status in VALID_STATUS else '❌ 非法（列表里看不到）'))
    print('     project_hid    : %s' % show(p.project_hid))
    print('     project_type   : %s' % show(p.project_type))
    print('     contact_person : %s' % show(p.contact_person))
    print('     remarks        : %s' % show(p.remarks))
    print('     folder_name    : %s' % show(p.folder_name))
    print('     created_at     : %s' % p.created_at)
    groups = TourGroup.query.filter_by(project_id=p.id).all()
    print('     团组数量        : %s' % len(groups))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=int, help='只看某个项目 ID')
    parser.add_argument('--fix', action='store_true', help='把非法状态改成合法状态')
    parser.add_argument('--to', default='处理中', help='--fix 时写入的状态，默认 处理中')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.id:
            p = TourProject.query.get(args.id)
            if not p:
                print('❌ 项目 %s 不存在' % args.id)
                return
            print('=== 项目 %s 明细 ===' % args.id)
            dump_project(p)
            targets = [p] if p.project_status not in VALID_STATUS else []
        else:
            print('=== 全表状态分布 ===')
            rows = db.session.query(TourProject.project_status, db.func.count(TourProject.id)) \
                .group_by(TourProject.project_status).all()
            for status, count in rows:
                flag = '✅' if status in VALID_STATUS else '❌ 非法'
                print('  %-12s %4d  %s' % (show(status), count, flag))

            targets = [p for p in TourProject.query.all() if p.project_status not in VALID_STATUS]
            print('')
            print('=== 状态非法的项目（在列表页任何标签下都看不到）: %s 个 ===' % len(targets))
            for p in targets:
                dump_project(p)

            print('')
            print('=== 最近创建的 10 个项目 ===')
            for p in TourProject.query.order_by(TourProject.id.desc()).limit(10).all():
                print('  id=%-5s %-12s %-40s %s' % (p.id, show(p.project_status),
                                                    p.project_name[:40], p.created_at))

        if not args.fix:
            if targets:
                print('')
                print('提示: 加 --fix 可把上述项目的状态改成「%s」' % args.to)
            return

        if args.to not in VALID_STATUS:
            print('❌ --to 必须是以下之一: %s' % ' / '.join(VALID_STATUS))
            return
        if not targets:
            print('没有需要修复的项目')
            return

        for p in targets:
            print('修复 id=%s: %s -> [%s]' % (p.id, show(p.project_status), args.to))
            p.project_status = args.to
        db.session.commit()
        print('✅ 已修复 %s 个项目' % len(targets))


if __name__ == '__main__':
    main()

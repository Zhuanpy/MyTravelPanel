"""
把日本签证项目的填表数据 seq 从「短名」迁移到「全限定名」。

背景：日本 PDF 有跨页同名字段(T5[0]/T14[0] 页1页2各一个)，原来按短名存/填会串页。
改用全限定名后，旧数据(短名)需迁移。冲突短名(T5[0]/T14[0])的旧值属申请人，映射到第1页。

幂等：已是全限定名(含'.')的跳过。
运行方式: python scripts/20260702_migrate_japan_form_data_qualified.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.visa.routes import visa_project as vp
from App_new.business.visa.models import VisaProject, VisaProjectFormData

app = create_app()

with app.app_context():
    # 先把 seq 列加宽到 120（全限定名较长；老表可能是 VARCHAR(20)）
    from sqlalchemy import text
    try:
        db.session.execute(text(
            'ALTER TABLE visa_project_form_data MODIFY COLUMN seq VARCHAR(120) NOT NULL'))
        db.session.commit()
        print('seq 列已确保为 VARCHAR(120)')
    except Exception as e:
        db.session.rollback()
        print(f'ALTER seq 列跳过/失败(可能已是120): {e}')

    # 短名 → 全限定名（冲突时优先第1页 PAGE01）
    short_to_qual = {}
    for f in vp._japan_template_fields():
        short = f['seq'].split('.')[-1]
        if short not in short_to_qual or f['page'] == 'PAGE01':
            short_to_qual[short] = (f['seq'], f['page'])

    projects = VisaProject.query.filter(VisaProject.visa_type.like('%日本%')).all()
    print(f'日本项目数: {len(projects)}')
    total = 0
    for p in projects:
        rows = VisaProjectFormData.query.filter_by(project_id=p.id).all()
        changed = 0
        for r in rows:
            if '.' in (r.seq or ''):
                continue  # 已是全限定名
            mapped = short_to_qual.get(r.seq)
            if not mapped:
                continue
            qual, page = mapped
            # 避免与已存在的目标 seq 冲突
            exists = VisaProjectFormData.query.filter_by(project_id=p.id, seq=qual).first()
            if exists and exists.id != r.id:
                db.session.delete(r)
            else:
                r.seq = qual
                r.page = page
            changed += 1
        if changed:
            db.session.commit()
            print(f'  项目{p.id} ({p.applicant_name}): 迁移 {changed} 条')
            total += changed

    # 修正 RB1(性别)旧值：M→0 / F→1（真实开关值是 0/1，非 M/F）
    from App_new.business.visa.models import VisaProjectFormData as VFD
    sex_fixed = 0
    for r in VFD.query.all():
        if r.seq and r.seq.split('.')[-1] in ('RB1[0]', 'RB1[1]') and r.detail in ('M', 'F'):
            r.detail = '0' if r.detail == 'M' else '1'
            sex_fixed += 1
    if sex_fixed:
        db.session.commit()
    print(f'完成，共迁移 {total} 条；RB1 性别值修正 {sex_fixed} 条')

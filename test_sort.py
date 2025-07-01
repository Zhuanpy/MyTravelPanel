from App import create_app
from App.models.projects.TourProject import TourGroup, TourItinerary
from App.exts import db

app = create_app()
app.app_context().push()

print('检查所有团数据:')
groups = TourGroup.query.all()
print(f'总团数量: {len(groups)}')

for group in groups:
    print(f'\n团ID: {group.id}, 项目ID: {group.project_id}, 团名称: {group.title}')
    itineraries = TourItinerary.query.filter_by(tour_id=group.id).order_by(TourItinerary.date.asc()).all()
    print(f'行程数量: {len(itineraries)}')
    for i in itineraries:
        print(f'  - 日期: {i.date}, 标题: {i.day_title}') 
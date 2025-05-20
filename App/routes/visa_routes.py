from flask import jsonify, request
from datetime import datetime
from App.models.VisaModels import FlightSegment
from App import db

@visa_routes.route('/flight_segments/add', methods=['POST'])
def add_flight_segment():
    """添加航段信息"""
    try:
        data = request.get_json()
        
        # 验证必要字段
        required_fields = ['flightNumber', 'departureCity', 'arrivalCity', 
                         'departureDate', 'departureTime', 'arrivalTime']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'缺少必要字段: {field}'}), 400
        
        # 创建新的航段记录
        new_segment = FlightSegment(
            project_id=data.get('projectId'),  # 需要从前端传入项目ID
            flight_number=data['flightNumber'],
            departure_city=data['departureCity'],
            arrival_city=data['arrivalCity'],
            departure_date=datetime.strptime(data['departureDate'], '%Y-%m-%d').date(),
            departure_time=datetime.strptime(data['departureTime'], '%H:%M').time() if data['departureTime'] else None,
            arrival_time=datetime.strptime(data['arrivalTime'], '%H:%M').time() if data['arrivalTime'] else None
        )
        
        db.session.add(new_segment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '航段添加成功',
            'data': {
                'id': new_segment.id,
                'flightNumber': new_segment.flight_number,
                'departureCity': new_segment.departure_city,
                'arrivalCity': new_segment.arrival_city,
                'departureDate': new_segment.departure_date.strftime('%Y-%m-%d'),
                'departureTime': new_segment.departure_time.strftime('%H:%M') if new_segment.departure_time else None,
                'arrivalTime': new_segment.arrival_time.strftime('%H:%M') if new_segment.arrival_time else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@visa_routes.route('/flight_segments/delete', methods=['POST'])
def delete_flight_segment():
    """删除航段信息"""
    try:
        data = request.get_json()
        segment_id = data.get('segmentId')
        
        if not segment_id:
            return jsonify({'success': False, 'message': '缺少航段ID'}), 400
            
        segment = FlightSegment.query.get(segment_id)
        if not segment:
            return jsonify({'success': False, 'message': '航段不存在'}), 404
            
        db.session.delete(segment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '航段删除成功'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500 
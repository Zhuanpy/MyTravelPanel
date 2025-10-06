from ..models.models import FlightSchedule
from sqlalchemy.exc import IntegrityError
from flask import current_app as app
from App_new.exts import db
from App_new.utils.cache import simple_cache

class FlightService:
    @staticmethod
    def create_or_update_schedule(form_data):
        try:
            flight_number = form_data.get('flight_number', '').replace(" ", "").upper()
            schedule_city = form_data.get('schedule_city', '').replace(" ", "").upper()
            schedule_timing = form_data.get('schedule_timing', '')
            
            # 新增字段
            departure_terminal = form_data.get('departure_terminal', 'Unknown')
            departure_gate = form_data.get('departure_gate', 'Unknown')
            arrival_terminal = form_data.get('arrival_terminal', 'Unknown')
            arrival_gate = form_data.get('arrival_gate', 'Unknown')
            aircraft = form_data.get('aircraft', 'Unknown')
            status = form_data.get('status', 'Unknown')
            
            if not all([flight_number, schedule_city, schedule_timing]):
                return {'success': False, 'message': '所有字段都是必填项。'}
            
            airline_code = flight_number[:2]
            airline_num = flight_number[2:]
            
            # 检查是否已存在该航班号的记录
            existing_flight = FlightSchedule.query.filter_by(flight_number=flight_number).first()
            
            if existing_flight:
                # 更新现有记录
                existing_flight.schedule_city = schedule_city
                existing_flight.schedule_timing = schedule_timing
                existing_flight.departure_terminal = departure_terminal
                existing_flight.departure_gate = departure_gate
                existing_flight.arrival_terminal = arrival_terminal
                existing_flight.arrival_gate = arrival_gate
                existing_flight.aircraft = aircraft
                existing_flight.status = status
                db.session.commit()
                try:
                    simple_cache.delete(f"schedule:{flight_number}")
                except Exception:
                    pass
                return {'success': True, 'message': f"航班 '{flight_number}' 更新成功。"}
            else:
                # 创建新记录
                new_flight = FlightSchedule(
                    flight_number=flight_number,
                    airline_code=airline_code,
                    airline_num=airline_num,
                    schedule_city=schedule_city,
                    schedule_timing=schedule_timing,
                    departure_terminal=departure_terminal,
                    departure_gate=departure_gate,
                    arrival_terminal=arrival_terminal,
                    arrival_gate=arrival_gate,
                    aircraft=aircraft,
                    status=status
                )
                db.session.add(new_flight)
                db.session.commit()
                try:
                    simple_cache.delete(f"schedule:{flight_number}")
                except Exception:
                    pass
                return {'success': True, 'message': f"航班 '{flight_number}' 添加成功。"}
                
        except IntegrityError:
            db.session.rollback()
            return {'success': False, 'message': f"错误：航班号 '{flight_number}' 已存在。"}
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error in create_or_update_schedule: {str(e)}")
            return {'success': False, 'message': f"发生错误：{str(e)}"}

    @staticmethod
    def get_schedule(flight_number: str) -> dict:
        """获取航班时刻表信息"""
        try:
            schedule = FlightSchedule.query.filter_by(
                flight_number=flight_number.strip().upper()
            ).first()
            return schedule.to_dict() if schedule else {}
        except Exception as e:
            app.logger.error(f"Error fetching flight schedule: {e}")
            return {} 
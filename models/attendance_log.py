from odoo import models, fields, api
import jwt
from datetime import datetime


class AttendanceLogDetails(models.Model):
    _name = 'attendance.log.details'
    _description = 'Attendance Log Details'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Person Name')
    employee_id = fields.Many2one('hr.employee')
    in_camera_id = fields.Many2one('res.camera')
    out_camera_id = fields.Many2one('res.camera')
    check_in_time = fields.Datetime()
    check_out_time = fields.Datetime()
    person_image = fields.Binary()
    face_image = fields.Binary()
    duration = fields.Char()

    @api.model
    def process_attendance_request(self, token, request_data):
        """
        Process attendance requests for entry and exit scenarios.
        :param token: JWT token string
        :param request_data: Dictionary containing the request details
        :return: Dictionary with status, created log IDs, and other details
        """
        try:
            # Decode the JWT token
            secret = "default_secret_key"  # Ensure this matches the encoding secret
            decoded_token = jwt.decode(token, secret, algorithms=["HS256"])

            # Check token validity
            user_id = decoded_token.get('user_id')
            expiry_time = decoded_token.get('exp')
            current_time = datetime.utcnow().timestamp()

            if current_time > expiry_time:
                return {"status": "error", "message": "Token has expired"}

            user = self.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {"status": "error", "message": "Invalid user ID in token"}

            # Extract values from the request
            person_name = request_data.get('name')
            camera_name = request_data.get('camera_id')
            passing_type = request_data.get('passing_type')
            check_time = request_data.get('check_in_time')
            person_image = request_data.get('person_image')
            face_image = request_data.get('face_image')

            # Check for employee based on name or create one
            employee_created = False
            employee_record = self.env['hr.employee'].sudo().search([('name', '=', person_name)], limit=1)
            if not employee_record:
                employee_record = self.env['hr.employee'].sudo().create({
                    'name': person_name,
                    'work_email': f"{person_name.lower().replace(' ', '.')}@example.com",  # Example email
                    'image_1920': person_image,  # Save image if provided
                })
                employee_created = True

            # Check for camera record
            camera_record = self.env['res.camera'].sudo().search([('name', '=', camera_name)], limit=1)
            if not camera_record:
                return {"status": "error", "message": f"Camera with name '{camera_name}' does not exist"}

            # Process entry
            if passing_type == 'entry':
                attendance_log = self.sudo().create({
                    'name': person_name,
                    'employee_id': employee_record.id,
                    'in_camera_id': camera_record.id,
                    'check_in_time': check_time,
                    'person_image': person_image,
                    'face_image': face_image,
                })
                return {
                    "status": "success",
                    "passing_type": "entry",
                    "check_in_time": attendance_log.check_in_time,
                    "created_log_ids": [attendance_log.id],
                    "employee_created": employee_created
                }

            # Process exit
            elif passing_type == 'exit':
                existing_log = self.sudo().search([
                    ('employee_id', '=', employee_record.id),
                    ('check_out_time', '=', False)
                ], limit=1)

                if not existing_log:
                    return {"status": "error", "message": "No open entry record found for this employee"}

                check_out_time = datetime.strptime(request_data.get('check_in_time'), "%Y-%m-%d %H:%M:%S")
                check_in_time = existing_log.check_in_time
                duration = check_out_time - check_in_time

                existing_log.sudo().write({
                    'out_camera_id': camera_record.id,
                    'check_out_time': check_time,
                    'duration': str(duration),
                })

                return {
                    "status": "success",
                    "passing_type": "exit",
                    "check_in_time": check_in_time,
                    "check_out_time": check_out_time,
                    "created_log_ids": [existing_log.id],
                    "duration": str(duration)
                }

            else:
                return {"status": "error", "message": "Invalid passing type"}

        except jwt.ExpiredSignatureError:
            return {"status": "error", "message": "Token has expired"}
        except jwt.InvalidTokenError:
            return {"status": "error", "message": "Invalid token"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

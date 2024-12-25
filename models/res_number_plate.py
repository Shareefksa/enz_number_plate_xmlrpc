from odoo import fields, models, api, _
import jwt
from datetime import datetime


class ResNumberPlate(models.Model):
    _name = 'res.number.plate'
    _description = 'Res Number Plate'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Number Plate", required=True)
    active = fields.Boolean(default=True)
    vehicle_image = fields.Binary(string="Vehicle Image")

    @api.model
    def fetch_all_details(self, token):
        """Fetch details from all models if token is valid."""
        # Secret key to validate the token (make sure this matches your encoding key)
        secret = "default_secret_key"

        try:
            # Decode the token
            decoded_token = jwt.decode(token, secret, algorithms=["HS256"])

            # Extract user details from the token
            user_id = decoded_token.get('user_id')
            expiry_time = decoded_token.get('exp')

            # Check if the token is expired
            current_time = datetime.utcnow().timestamp()
            if current_time > expiry_time:
                return {"status": "error", "message": "Token has expired"}

            # Verify the user exists and is active
            user = self.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {"status": "error", "message": "Invalid user ID in token"}

            # Token is valid, fetch details from each model
            number_plate_records = self.env['res.number.plate'].search([('active', '=', True)])
            # camera_records = self.env['res.camera'].search([('active', '=', True)])
            detection_service_records = self.env['res.detection.services'].search([('active', '=', True)])
            parking_rate_records = self.env['res.parking.rate'].search([('active', '=', True)])

            result = {
                'number_plates': [
                    {
                        'id': record.id,
                        'name': record.name,
                        'active': record.active
                    } for record in number_plate_records
                ],
                # 'cameras': [
                #     {
                #         'id': record.id,
                #         'name': record.name,
                #         'service_id': record.service_id.name if record.service_id else None,
                #         'service_type': record.service_type,
                #         'register_new_plate': record.register_new_plate,
                #         'pay_park': record.pay_park,
                #         'active': record.active
                #     } for record in camera_records
                # ],
                'detection_services': [
                    {
                        'id': record.id,
                        'name': record.name,
                        'active': record.active
                    } for record in detection_service_records
                ],
                'parking_rates': [
                    {
                        'id': record.id,
                        'duration_in_hours': record.duration_in_hours,
                        'amount': record.amount,
                        'active': record.active
                    } for record in parking_rate_records
                ]
            }

            return {
                'status': 'success',
                'details': result
            }

        except jwt.ExpiredSignatureError:
            return {'status': 'error', 'message': 'Token expired'}
        except jwt.InvalidTokenError:
            return {'status': 'error', 'message': 'Invalid token'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


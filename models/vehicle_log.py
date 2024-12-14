from odoo import models, fields, api
import jwt
from datetime import datetime


class VehicleLogDetails(models.Model):
    _name = 'vehicle.log.details'
    _description = 'Vehicle Log Details'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Plate Number')
    plate_id = fields.Many2one('res.number.plate')
    in_camera_id = fields.Many2one('res.camera')
    out_camera_id = fields.Many2one('res.camera')
    check_in_time = fields.Datetime()
    check_out_time = fields.Datetime()
    vehicle_image = fields.Binary()
    body_image = fields.Binary()
    duration = fields.Char()
    amount = fields.Float()

    @api.model
    def create_multiple_vehicle_logs(self, token, logs_data):
        """
        Create multiple vehicle log records after validating the JWT token.
        :param token: JWT token string
        :param logs_data: List of dictionaries, each containing log details
        :return: Dictionary with status, created log IDs, and errors (if any)
        """
        try:
            # Decode the JWT token
            secret = "default_secret_key"  # Same secret used for encoding the token
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

            created_logs = []
            errors = []

            for log_data in logs_data:
                plate_number = log_data.get('name')
                plate_record = self.env['res.number.plate'].sudo().search([('name', '=', plate_number)], limit=1)

                if not plate_record:
                    errors.append(f"Plate number '{plate_number}' does not exist")
                    continue

                log_data['plate_id'] = plate_record.id
                vehicle_log = self.sudo().create(log_data)
                created_logs.append(vehicle_log.id)

            return {
                "status": "success" if created_logs else "error",
                "created_log_ids": created_logs,
                "errors": errors
            }

        except jwt.ExpiredSignatureError:
            return {"status": "error", "message": "Token has expired"}
        except jwt.InvalidTokenError:
            return {"status": "error", "message": "Invalid token"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @api.model
    def process_parking_request(self, token, request_data):
        """
        Process parking requests for entry and exit scenarios.
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

            plate_number = request_data.get('name')
            parking_type = request_data.get('parking_type')
            camera_name = request_data.get('camera_id')
            vehicle_image = request_data.get('vehicle_image')
            body_image = request_data.get('body_image')

            # Find camera record
            camera_record = self.env['res.camera'].sudo().search([('name', '=', camera_name)], limit=1)
            if not camera_record:
                return {"status": "error", "message": f"Camera with name '{camera_name}' does not exist"}

            # Check if the camera has pay_park enabled
            if camera_record.pay_park:
                # Camera is configured for paid parking
                plate_record = self.env['res.number.plate'].sudo().search([('name', '=', plate_number)], limit=1)
                if not plate_record:
                    # If no plate exists, create a new plate record
                    plate_record = self.env['res.number.plate'].sudo().create({
                        'name': plate_number,
                        'vehicle_image': vehicle_image,
                    })
                    plate_created = True
                else:
                    plate_created = False
            else:
                # If camera doesn't have pay_park enabled, ignore amount calculation logic
                plate_record = self.env['res.number.plate'].sudo().search([('name', '=', plate_number)], limit=1)
                if not plate_record:
                    if camera_record.register_new_plate:
                        plate_record = self.env['res.number.plate'].sudo().create({
                            'name': plate_number,
                            'vehicle_image': vehicle_image,
                        })
                        plate_created = True
                    else:
                        return {"status": "error", "message": f"Plate number '{plate_number}' does not exist"}
                else:
                    plate_created = False


            if parking_type == 'entry':
                # Create new log entry for entry parking
                vehicle_log = self.sudo().create({
                    'name': plate_number,
                    'plate_id': plate_record.id,
                    'in_camera_id': camera_record.id,
                    'check_in_time': request_data.get('check_in_time'),
                    'vehicle_image': vehicle_image,
                    'body_image': body_image,
                })
                return {
                    "status": "success",
                    "number_plate": plate_number,
                    "parking_type": "entry",
                    "check_in_time": vehicle_log.check_in_time,
                    "created_log_ids": [vehicle_log.id],
                    "plate_created": plate_created,  # Whether a new plate was created
                }

            elif parking_type == 'exit':
                # Handle exit parking
                existing_log = self.sudo().search([
                    ('plate_id', '=', plate_record.id),
                    ('check_out_time', '=', False)
                ], limit=1)

                if not existing_log:
                    return {"status": "error", "message": "No open entry record found for this plate number"}

                check_out_time = datetime.strptime(request_data.get('check_in_time'), "%Y-%m-%d %H:%M:%S")
                check_in_time = existing_log.check_in_time
                duration = check_out_time - check_in_time

                if camera_record.pay_park:
                    # Calculate the duration in hours and amount only if pay_park is enabled
                    duration_in_hours = round(duration.total_seconds() / 3600.0 , 2) # Convert seconds to hours

                    # Find all applicable parking rates
                    parking_rates = self.env['res.parking.rate'].sudo().search([], order="duration_in_hours asc")

                    if not parking_rates:
                        return {"status": "error", "message": "No parking rates configured"}

                    # Initialize the parking amount
                    parking_amount = 0

                    # Case 1: If duration is less than the smallest configured rate
                    if duration_in_hours < parking_rates[0].duration_in_hours:
                        parking_amount = parking_rates[0].amount
                    # Case 2: If duration is greater than the largest configured rate
                    elif duration_in_hours > parking_rates[-1].duration_in_hours:
                        parking_amount = parking_rates[-1].amount
                    # Case 3: If duration matches exactly a configured rate
                    elif any(rate.duration_in_hours == duration_in_hours for rate in parking_rates):
                        parking_amount = next(
                            rate.amount for rate in parking_rates if rate.duration_in_hours == duration_in_hours)
                    # Case 4: If duration is between two rates, take the higher rate
                    else:
                        for i in range(1, len(parking_rates)):
                            lower_rate = parking_rates[i - 1]
                            upper_rate = parking_rates[i]
                            if lower_rate.duration_in_hours < duration_in_hours <= upper_rate.duration_in_hours:
                                parking_amount = upper_rate.amount
                                break

                    # Update the existing log with checkout details
                    existing_log.sudo().write({
                        'out_camera_id': camera_record.id,
                        'check_out_time': request_data.get('check_in_time'),
                        'amount': parking_amount,
                        'duration': str(duration),
                    })

                    return {
                        "status": "success",
                        "number_plate": plate_number,
                        "parking_type": "exit",
                        "check_in_time": check_in_time,
                        "check_out_time": check_out_time,
                        "created_log_ids": [existing_log.id],
                        "duration": str(duration),
                        "duration_in_hours": duration_in_hours,
                        "amount": parking_amount,  # Return the calculated amount
                        "plate_created": plate_created,  # Whether a new plate was created
                    }
                else:
                    # If pay_park is not enabled, return exit details without the amount
                    existing_log.sudo().write({
                        'out_camera_id': camera_record.id,
                        'check_out_time': request_data.get('check_in_time'),
                        'duration': str(duration),
                    })

                    return {
                        "status": "success",
                        "number_plate": plate_number,
                        "parking_type": "exit",
                        "check_in_time": check_in_time,
                        "check_out_time": check_out_time,
                        "created_log_ids": [existing_log.id],
                        "duration": str(duration),
                        "plate_created": plate_created,  # Whether a new plate was created
                    }

            else:
                return {"status": "error", "message": "Invalid parking type"}

        except jwt.ExpiredSignatureError:
            return {"status": "error", "message": "Token has expired"}
        except jwt.InvalidTokenError:
            return {"status": "error", "message": "Invalid token"}
        except Exception as e:
            return {"status": "error", "message": str(e)}









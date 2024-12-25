from odoo import models, api,_
import uuid
import jwt
from datetime import datetime, timedelta
from odoo import fields,models
from odoo.exceptions import UserError

class ResUsers(models.Model):
    _inherit = 'res.users'


    token_for_user = fields.Char()
    token_validity_hours = fields.Integer(default=1)
    subscription_type = fields.Selection([('online','Online'),('offline','Offline'),('hybrid','Hybrid')],default='online')


    @api.model
    def generate_auth_details(self, username, password):
        """
        Authenticate the user and generate API key and JWT token.

        :param username: Username of the user
        :param password: Password of the user
        :return: Dictionary containing API key, JWT token, expiry, and user details
        """
        try:
            # print('details')
            # Authenticate user
            user = self.sudo().search([('login', '=', username)], limit=1)
            # if not user or not user._check_credentials(password):
            #     return {"status": "error", "message": "Invalid username or password"}

            # Generate API key
            api_key = str(uuid.uuid4())

            # Generate JWT token
            secret_key = "default_secret_key"
            payload = {
                "user_id": user.id,
                "api_key": api_key,
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(hours=user.token_validity_hours),  # Token valid for 1 hour
            }
            token = jwt.encode(payload, secret_key, algorithm="HS256")
            self.token_for_user = token

            # Prepare response
            response = {
                "status": "success",
                "user": user.name,
                "api_key": api_key,
                "token": token,
                "expiry": (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                "secret_key": secret_key,
                "user_id":user.id,
                "subscription_type":user.subscription_type,
            }

            return response
        except Exception as e:
            return ({"status": "error", "message": str(e)})

    # @api.model
    # def generate_auth_details_initial(self, username, password):
    #     """
    #     Authenticate the user and generate API key and JWT token.
    #
    #     :param username: Username of the user
    #     :param password: Password of the user
    #     :return: Dictionary containing API key, JWT token, expiry, and user details
    #     """
    #     try:
    #         # print('details')
    #         # Authenticate user
    #         user = self.sudo().search([('login', '=', username)], limit=1)
    #         # if not user or not user._check_credentials(password):
    #         #     return {"status": "error", "message": "Invalid username or password"}
    #
    #         # Generate API key
    #         api_key = str(uuid.uuid4())
    #
    #         # Generate JWT token
    #         secret_key = "default_secret_key"
    #         payload = {
    #             "user_id": user.id,
    #             "api_key": api_key,
    #             "iat": datetime.utcnow(),
    #             "exp": datetime.utcnow() + timedelta(hours=user.toke_validity_hours),  # Token valid for 1 hour
    #         }
    #         token = jwt.encode(payload, secret_key, algorithm="HS256")
    #         self.token_for_user = token
    #
    #         # Prepare response
    #         response = {
    #             "status": "success",
    #             "user": user.name,
    #             "api_key": api_key,
    #             "token": token,
    #             "expiry": (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
    #             "secret_key": secret_key,
    #             "user_id":user.id,
    #             "subscription_type":user.subscription_type,
    #         }
    #
    #         return response
    #     except Exception as e:
    #         return {"status": "error", "message": str(e)}

    @api.model
    def get_rtsp_link(self, token, mac_id):
        """
        Retrieve the RTSP link for a given MAC ID with JWT token verification.
        :param token: JWT token string
        :param mac_id: The MAC ID to search for
        :return: RTSP link as a string
        :raises UserError: If any validation or data retrieval fails
        """
        try:
            # Decode the JWT token
            secret = "default_secret_key"  # Replace with your secure secret key
            decoded_token = jwt.decode(token, secret, algorithms=["HS256"])

            # Verify token expiry
            user_id = decoded_token.get('user_id')
            expiry_time = decoded_token.get('exp')
            current_time = datetime.utcnow().timestamp()

            if current_time > expiry_time:
                raise UserError(_("Token has expired."))

            # Verify user ID in token
            user = self.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                raise UserError(_("Invalid user ID in token."))

            # Search for camera by MAC ID
            camera = self.env['res.camera'].sudo().search([('mac_id', '=', mac_id)], limit=1)
            if not camera:
                raise UserError(_("No camera found for MAC ID: %s") % mac_id)

            # Return the RTSP link
            if not camera.rtsp_link:
                raise UserError(_("RTSP link not configured for camera: %s") % camera.name)

            if not camera.service_type:
                raise UserError(_("Service Type Not Configured: %s") % camera.name)
            rtsp_details = {
                'rtsp_link' : camera.rtsp_link,
                'service_type' : camera.service_type
            }


            return rtsp_details

        except jwt.ExpiredSignatureError:
            raise UserError(_("Token has expired."))
        except jwt.InvalidTokenError:
            raise UserError(_("Invalid token."))
        except Exception as e:
            raise UserError(_("An error occurred: %s") % str(e))


    @api.model
    def update_camera_image(self, token, mac_id, camera_image_base64):
        """
        Update camera image in the 'res.camera' model based on the MAC ID with JWT token verification.
        :param token: JWT token string
        :param mac_id: The MAC ID of the camera
        :param camera_image_base64: The camera image data in base64 format
        :return: A dictionary with status and message
        :raises UserError: If any validation or data retrieval fails
        """
        try:
            # Decode the JWT token
            secret = "default_secret_key"  # Replace with your secure secret key
            decoded_token = jwt.decode(token, secret, algorithms=["HS256"])

            # Verify token expiry
            user_id = decoded_token.get('user_id')
            expiry_time = decoded_token.get('exp')
            current_time = datetime.utcnow().timestamp()

            if current_time > expiry_time:
                raise UserError(_("Token has expired."))

            # Verify user ID in token
            user = self.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                raise UserError(_("Invalid user ID in token."))

            # Search for the camera record by MAC ID
            camera = self.env['res.camera'].search([('mac_id', '=', mac_id)], limit=1)
            if not camera:
                raise UserError(_("Camera with MAC ID %s not found.") % mac_id)

            # Convert base64 camera image data and update the camera image field
            camera_image_data = camera_image_base64
            camera.write({'camera_image': camera_image_data})

            return {"status": "success", "message": "Camera image updated successfully."}

        except jwt.ExpiredSignatureError:
            raise UserError(_("Token has expired."))
        except jwt.InvalidTokenError:
            raise UserError(_("Invalid token."))
        except Exception as e:
            raise UserError(_("An error occurred: %s") % str(e))

    @api.model
    def get_camera_coordinates(self, token, mac_id):
        """
        Fetch camera coordinates from 'res.camera' model based on the MAC ID with JWT token verification.
        :param token: JWT token string
        :param mac_id: The MAC ID of the camera
        :return: A JSON dictionary with the camera coordinates (x1, y1, x2, y2)
        :raises UserError: If any validation or data retrieval fails
        """
        try:
            # Decode the JWT token
            secret = "default_secret_key"  # Replace with your secure secret key
            decoded_token = jwt.decode(token, secret, algorithms=["HS256"])

            # Verify token expiry
            user_id = decoded_token.get('user_id')
            expiry_time = decoded_token.get('exp')
            current_time = datetime.utcnow().timestamp()

            if current_time > expiry_time:
                raise UserError(_("Token has expired."))

            # Verify user ID in token
            user = self.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                raise UserError(_("Invalid user ID in token."))

            # Search for the camera record by MAC ID
            camera = self.env['res.camera'].search([('mac_id', '=', mac_id)], limit=1)
            if not camera:
                raise UserError(_("Camera with MAC ID %s not found.") % mac_id)

            # Return camera coordinates in JSON format
            camera_data = {
                'mac_id': camera.mac_id,
                'x1': camera.x1,
                'y1': camera.y1,
                'x2': camera.x2,
                'y2': camera.y2,
                'status':'success'
            }

            return camera_data  # Convert to JSON format

        except jwt.ExpiredSignatureError:
            raise UserError(_("Token has expired."))
        except jwt.InvalidTokenError:
            raise UserError(_("Invalid token."))
        except Exception as e:
            raise UserError(_("An error occurred: %s") % str(e))

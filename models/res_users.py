from odoo import models, api
import uuid
import jwt
from datetime import datetime, timedelta
from odoo import fields,models


class ResUsers(models.Model):
    _inherit = 'res.users'


    token_for_user = fields.Char()
    toke_validity_hours = fields.Integer(default=1)
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
                "exp": datetime.utcnow() + timedelta(hours=user.toke_validity_hours),  # Token valid for 1 hour
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

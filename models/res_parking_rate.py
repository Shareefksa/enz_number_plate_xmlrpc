from odoo import fields,models


class ResParkingRate(models.Model):
    _name = 'res.parking.rate'
    _description = 'Parking Rate Configuration'
    _rec_name = 'duration_in_hours'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    duration_in_hours = fields.Float(string="Duration (hours)", required=True)
    amount = fields.Float(string="Amount", required=True, help="Rate for the specified duration")
    active = fields.Boolean(default=True)

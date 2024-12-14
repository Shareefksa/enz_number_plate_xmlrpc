from odoo import fields,models

class ResDetectionServices(models.Model):
    _name = 'res.detection.services'
    _description = 'Res Detection Services'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char()
    active = fields.Boolean(default=True)

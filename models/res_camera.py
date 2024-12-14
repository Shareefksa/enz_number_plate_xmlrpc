from odoo import fields,models,api

class ResCamera(models.Model):
    _name = 'res.camera'
    _description = 'Res Camera'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    service_id = fields.Many2one('res.detection.services')
    service_type = fields.Selection([('entry','Entry'),('exit','Exit')],default="entry")
    active = fields.Boolean(default=True)
    register_new_plate = fields.Boolean()
    pay_park = fields.Boolean()

    @api.onchange('pay_park')
    def compute_register_plate(self):
        if self.pay_park == True:
            self.register_new_plate = True

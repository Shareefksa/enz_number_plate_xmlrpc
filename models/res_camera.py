from odoo import fields, models, api
from io import BytesIO
from PIL import Image, ImageDraw
import base64
from odoo.exceptions import ValidationError
class ResCamera(models.Model):
    _name = 'res.camera'
    _description = 'Res Camera'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    mac_id = fields.Char()
    service_id = fields.Many2one('res.detection.services')
    service_type = fields.Selection([('entry', 'Entry'), ('exit', 'Exit')], default="entry")
    active = fields.Boolean(default=True)
    register_new_plate = fields.Boolean()
    pay_park = fields.Boolean()
    rtsp_link = fields.Char()
    x1 = fields.Integer()
    y1 = fields.Integer()
    x2 = fields.Integer()
    y2 = fields.Integer()
    line_y = fields.Integer()
    camera_image = fields.Binary()
    result_camera_image = fields.Binary()
    ip_address = fields.Char()
    status = fields.Selection([('draft','Draft'),('rtsp_check','Rtsp Check Success'),('image_updated','Image Updated'),('image_approved','Image Approved'),('retry','Retry')],default="draft")

    def process_image(self):
        """
        Processes the image by drawing a red rectangle based on coordinates
        and a horizontal line at a distance `line_y` from the top of the rectangle.
        Updates the result in result_camera_image.
        """
        for record in self:
            if not record.camera_image:
                raise ValidationError("Please upload an image in 'Camera Image' field before processing.")

            if not all([record.x1, record.y1, record.x2, record.y2]):
                raise ValidationError("Please provide all coordinates (X1, Y1, X2, Y2) before processing.")

            if not record.line_y:
                raise ValidationError("Please provide the `line_y` value before processing.")

            # Decode the binary image
            image_data = base64.b64decode(record.camera_image)
            image = Image.open(BytesIO(image_data))

            # Draw the rectangle on the image
            draw = ImageDraw.Draw(image)
            draw.rectangle([(record.x1, record.y1), (record.x2, record.y2)], outline="blue", width=3)

            # Draw the horizontal line
            line_position = record.y1 + record.line_y
            if line_position > record.y2 or line_position < record.y1:
                raise ValueError("The `line_y` value exceeds the rectangle's boundaries.")

            draw.line([(record.x1, line_position), (record.x2, line_position)], fill="red", width=2)

            # Save the processed image back to binary
            output = BytesIO()
            image.save(output, format=image.format)
            processed_image_data = base64.b64encode(output.getvalue())
            record.result_camera_image = processed_image_data

    @api.onchange('pay_park')
    def compute_register_plate(self):
        if self.pay_park:
            self.register_new_plate = True

# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class RepairRequest(models.Model):
    _name = 'repair_request.repair_request'
    _inherit = "mail.thread"
    _description = 'Repair Request'

    repair_request_name = fields.Char(string="Repair Request Name")
    repair_reference = fields.Char(string="Repair Reference", copy=False, readonly=True,
                                   default='New')
    description = fields.Text(string="Description")
    client_email = fields.Char(string="Client Email")
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    product_name = fields.Char(string="Product to Repair")
    repair_image = fields.Many2many('ir.attachment', 'repair_request_image_rel', 'request_id', 'attachment_id',
                                    string='Repair Images', attachment=True)
    under_warranty = fields.Boolean(string="Under Warranty")
    scheduled_date = fields.Datetime(string="Scheduled Date")
    responsible_user_id = fields.Many2one('res.users', string="Responsible")
    component_status = fields.Selection(
        [('green', 'Available'), ('red', 'Unavailable')],
        string="Component Status",
        default='red'
    )
    status = fields.Selection(
        [('new', 'New'),
         ('quotation', 'Quotation'),
         ('client_review', 'Client Review'),
         ('accepted', 'Accepted'),
         ('cancel', 'Cancelled')],
        string='Status',
        default='new',
        required=True,
        tracking=True
    )
    quotation_id = fields.Many2one('sale.order', string="Quotation", readonly=True)
    sale_order_id = fields.Many2one('sale.order', string="Sales Order", readonly=True)
    part_ids = fields.One2many('repair_request.parts', 'repair_request_id', string='Parts')
    repair_notes = fields.Text(string='Repair Notes')

    @api.model
    def create(self, vals):
        if not vals.get('product_name'):
            raise UserError("The field 'Product' is required.")
        if vals.get('repair_reference', 'New') == 'New':
            vals['repair_reference'] = self.env['ir.sequence'].next_by_code('repair_request.repair_request') or 'New'
        return super(RepairRequest, self).create(vals)

    def generate_quotation_button_method(self):
        sale_order_lines = []
        for part in self.part_ids:
            sale_order_lines.append((0, 0, {
                'product_id': part.product_id.id,
                'product_uom_qty': part.demand,
                'price_unit': part.product_id.lst_price,
                'name': part.product_id.name,
            }))

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': sale_order_lines,
        })
        self.quotation_id = sale_order.id
        self.status = 'quotation'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Quotation',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
        }

    def send_for_review_button_method(self):
        for record in self:
            if record.status != 'quotation':
                raise UserError("Cannot send for client review until a quotation is generated.")

            # TODO: Send emails asynchronously

            # Post a message to each member of the design team
            subject = "Repair Request Review"
            body = f"""
                       <p>Dear {record.partner_id.name},</p>
                       <p>Your repair request (<b>{record.product_name}</b>) is ready for review. Please log in to the portal to review the details.</p>
                       <p>Best regards,<br/>Sales Team</p>
                       """
            email_values = {
                'subject': subject,

                'body_html': body,
                'email_to': record.client_email,  # Assuming each member has a work_email field
            }
            mail = record.env['mail.mail'].create(email_values)
            # Send the email
            mail.send()

            record.status = 'client_review'

    def cancel_button_method(self):
        for record in self:
            if record.status in ['quotation', 'client_review']:
                raise UserError("Cannot move to 'Cancelled' once a quotation is generated or sent for client review.")
            record.status = 'cancel'

    def accept_quotation(self):
        if self.quotation_id:
            self.quotation_id.sudo().action_confirm()
            self.sale_order_id = self.quotation_id.id
            self.status = 'accepted'

    class RepairParts(models.Model):
        _name = 'repair_request.parts'
        _description = 'Repair Parts'

        repair_request_id = fields.Many2one('repair_request.repair_request', string='Repair Request', required=True,
                                            ondelete='cascade')
        part_type = fields.Selection([('add', 'Add'), ('replace', 'Replace')], string='Type', required=True, default='add')
        product_id = fields.Many2one('product.product', string='Product', required=True)
        demand = fields.Float(string='Demand', required=True)
        done = fields.Float(string='Done')
        used = fields.Boolean(string='Used', default=False)

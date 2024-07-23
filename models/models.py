# -*- coding: utf-8 -*-

from odoo import models, fields, api


class RepairRequest(models.Model):
    _name = 'repair_request.repair_request'
    _inherit = "mail.thread"
    _description = 'Repair Request'

    repair_request_name = fields.Char(string="Repair Request Name", required=True)
    description = fields.Text(string="Description")
    repair_image = fields.Binary(string="Repair Image", attachment=True)
    status = fields.Selection(
        [('new', 'New'),
         ('quotation', 'Quotation'),
         ('client_review', 'Client Review'),
         ('cancel', 'Cancelled')],
        string='Status',
        default='new',
        required=True,
        tracking=True
    )
    def generate_quotation_button_method(self):
        self.status = 'quotation'
    def send_for_review_button_method(self):
        self.status = 'client_review'
    def cancel_button_method(self):
        self.status = 'cancel'

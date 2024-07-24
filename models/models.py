# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class RepairRequest(models.Model):
    _name = 'repair_request.repair_request'
    _inherit = "mail.thread"
    _description = 'Repair Request'

    repair_request_name = fields.Char(string="Repair Request Name", required=True)
    description = fields.Text(string="Description")
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    repair_image = fields.Binary(string="Repair Image", attachment=True)
    status = fields.Selection(
        [('new', 'New'),
         ('quotation', 'Quotation'),
         ('client_review', 'Client Review'),
         ('cancel', 'Cancelled'),
         ('accepted', 'Accepted')],
        string='Status',
        default='new',
        required=True,
        tracking=True
    )
    quotation_id = fields.Many2one('sale.order', string="Quotation")
    sale_order_id = fields.Many2one('sale.order', string="Sales Order")

    def send_for_review_button_method(self):
        self.status = 'client_review'
    def cancel_button_method(self):
        self.status = 'cancel'

    def generate_quotation_button_method(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [(0, 0, {
                'product_id': self.product_id.id,
                'product_uom_qty': 1,
                'price_unit': self.product_id.lst_price,
                'name': self.description,
            })],
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

    def accept_quotation(self):
        if self.quotation_id:
            self.quotation_id.action_confirm()
            self.sale_order_id = self.quotation_id.id
            self.status = 'accepted'





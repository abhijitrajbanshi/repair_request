# -*- coding: utf-8 -*-

from odoo import models, fields, api


class RepairRequest(models.Model):
    _name = 'repair_request.repair_request'
    _description = 'Repair Request'

    repair_request_name = fields.Char(string="Repair Request Name", required=True)
    description = fields.Text(string="Description")
    repair_image = fields.Binary(string="Repair Image", attachment=True)
    status = fields.Selection(
        [('new', 'New'),
         ('client_review', 'Client Review'),
         ('completed', 'Completed')],
        string='Status',
        default='new',
        required=True
    )

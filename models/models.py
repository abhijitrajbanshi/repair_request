# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
from datetime import datetime, timedelta

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
    date_start = fields.Datetime(string="Scheduled Date")
    date = fields.Date(string='Expiration Date', index=True, tracking=True,
                       help="Date on which this project ends. The timeframe defined on the project is taken into account when viewing its planning.")
    responsible_user_id = fields.Many2one('res.users', string="Responsible", tracking=True)
    repair_deadline = fields.Datetime(string="Customer's Repair Deadline")
    completion_date = fields.Datetime(string="Completion Date")
    is_past_due = fields.Boolean(string="Is Past Due", compute='_compute_is_past_due', store=True)

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
         ('in_progress', 'In Progress'),
         ('completed', 'Completed'),
         ('cancel', 'Cancelled')],
        string='Status',
        default='new',
        required=True,
        tracking=True
    )
    quotation_id = fields.Many2one('sale.order', string="Quotation", readonly=True)
    sale_order_id = fields.Many2one('sale.order', string="Sales Order", readonly=True)
    part_ids = fields.One2many('repair_request.parts', 'repair_request_id', string='Parts')

    timesheet_ids = fields.One2many('repair_request.timesheet', 'repair_request_id', string='Timesheets')
    timer_start = fields.Datetime(string="Timer Start")
    is_timer_running = fields.Boolean(string="Is Timer Running", default=False)
    timer_paused_at = fields.Datetime(string="Timer Paused At")

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

    class RepairTimesheet(models.Model):
        _name = 'repair_request.timesheet'
        _description = 'Repair Timesheet'

        repair_request_id = fields.Many2one('repair_request.repair_request', string='Repair Request', required=True,
                                            ondelete='cascade')
        employee_id = fields.Many2one('res.users', string='Employee', required=True)
        date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
        description = fields.Char(string='Description')
        hours_spent = fields.Float(string='Hours Spent')

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

    @api.depends('repair_deadline', 'status')
    def _compute_is_past_due(self):
        for record in self:
            record.is_past_due = bool(record.repair_deadline and record.repair_deadline < fields.Datetime.now() and record.status != 'completed')


    def start_repair(self):
        for record in self:
            if record.status not in ['accepted', 'in_progress']:
                raise UserError("Repair cannot be started unless it is accepted or already in progress.")
            record.status = 'in_progress'
            record.is_timer_running = True
            record.timer_start = fields.Datetime.now()
            record.timer_paused_at = False
            record.create_time_log('started')

    def pause_timer(self):
        for record in self:
            if record.is_timer_running:
                record.timer_paused_at = fields.Datetime.now()
                record.is_timer_running = False

    def resume_timer(self):
        for record in self:
            if not record.is_timer_running and record.timer_paused_at:
                record.timer_start += fields.Datetime.now() - record.timer_paused_at
                record.is_timer_running = True
                record.timer_paused_at = False

    def stop_timer(self):
        for record in self:
            if record.is_timer_running:
                time_spent = fields.Datetime.now() - record.timer_start
                record.timesheet_ids.create({
                    'repair_request_id': record.id,
                    'employee_id': self.env.user.id,
                    'date': fields.Date.today(),
                    'description': '/',
                    'hours_spent': time_spent.total_seconds() / 3600.0,
                })
                record.is_timer_running = False
                record.timer_start = False
                record.timer_paused_at = False
                record.create_time_log('stopped')

    def complete_repair(self):
        for record in self:
            if record.status != 'in_progress':
                raise UserError("Repair can only be completed if it is in progress.")
            record.status = 'completed'
            record.completion_date = fields.Datetime.now()
            record.stop_timer()

    @api.depends('hours_spent')
    def _compute_total_hours(self):
        for record in self:
            record.total_hours = sum(line.hours_spent for line in record.timesheet_ids)

    def create_time_log(self, action):
        now = fields.Datetime.now()
        message = f"Timer {action} at: {now.strftime('%m/%d/%Y %H:%M:%S')}"
        self.message_post(body=message)





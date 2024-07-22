# -- coding: utf-8 --
import base64

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal as CustomerPortal
from odoo.http import request, route

class CustomerPortalHome(CustomerPortal):
    @http.route(['/my/repair_requests'], type='http', auth="user", website=True)
    def lists(self, **kw):
        repair_requests = request.env['repair_request.repair_request'].sudo().search([])
        return request.render("repair_request.repair_lists", {'repair_requests': repair_requests})

    @http.route(['/my/create-request'], type='http', auth="user", website=True)
    def create_request(self, **kw):
        return request.render("repair_request.create_repair_request", {})

    @http.route(['/my/create-request/submit'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def submit_request(self, **kw):
        repair_request_name = kw.get('repair_request_name')
        description = kw.get('repair_request_description')
        repair_image = request.httprequest.files.get('repair_image')
        repair_image_data = False

        if repair_image:
            repair_image_data = base64.b64encode(repair_image.read()).decode('utf-8')

        if repair_request_name:
            request.env['repair_request.repair_request'].create({
                'repair_request_name': repair_request_name,
                'description': description,
                'repair_image': repair_image_data,
            })
        return request.redirect('/my/repair_requests')

    @http.route('/my/repair_requests/<int:repair_id>', type='http', auth="user", website=True)
    def view_repair_request(self, repair_id, **kw):
        repair_request = request.env['repair_request.repair_request'].browse(repair_id)
        if not repair_request.exists():
            return request.redirect('/my/repair_requests')
        return request.render("repair_request.repair_request_template", {'repair_request': repair_request})

    



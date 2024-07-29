# -- coding: utf-8 --
import base64
import logging
logger = logging.getLogger(__name__)
from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal as CustomerPortal
from odoo.http import request, route


class CustomerPortalHome(CustomerPortal):
    @http.route(['/my/repair_requests'], type='http', auth="user", website=True)
    def lists(self, **kw):
        repair_requests = request.env['repair_request.repair_request'].sudo().search([('partner_id', '=', request.env.user.partner_id.id)])
        return request.render("repair_request.repair_lists",
                              {'repair_requests': repair_requests, 'page_name': "repair_lists"})

    @http.route(['/my/create-request'], type='http', auth="user", website=True)
    def create_request(self, **kw):
        products = request.env['product.product'].sudo().search([])
        error_message = request.session.pop('error_message', None)
        success_message = request.session.pop('success_message', None)
        return request.render("repair_request.create_repair_request",
                              {'page_name': "create_request", 'products': products, 'error_message': error_message,
                               'success_message': success_message})

    @http.route(['/my/create-request/submit'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def submit_request(self, **kw):
        repair_request_name = kw.get('repair_request_name')
        description = kw.get('repair_request_description')
        product_name = kw.get('product_name')
        repair_image = request.httprequest.files.get('repair_image')
        repair_image_data = False

        # Validate required fields
        if not repair_request_name or not description or not product_name:
            request.session['error_message'] = "Please provide all required information."
            return request.redirect('/my/create-request')

        # Validate image
        if repair_image:
            repair_image_data = base64.b64encode(repair_image.read()).decode('utf-8')
        else:
            request.session['error_message'] = "Please upload an image of the item."
            return request.redirect('/my/create-request')

        # Create the repair request
        request.env['repair_request.repair_request'].sudo().create({
            'repair_request_name': repair_request_name,
            'product_name': product_name,
            'client_email': request.env.user.email,
            'description': description,
            'repair_image': repair_image_data,
            'partner_id': request.env.user.partner_id.id,
        })

        # Set success message
        request.session['success_message'] = "Repair request submitted successfully."
        request.session.pop('success_message', None)
        return request.redirect('/my/repair_requests')

    @http.route('/my/repair_requests/<int:repair_id>', type='http', auth="user", website=True)
    def view_repair_request(self, repair_id, **kw):
        repair_request = request.env['repair_request.repair_request'].browse(repair_id)
        if not repair_request.exists() or repair_request.partner_id.id != request.env.user.partner_id.id:
            return request.redirect('/my/repair_requests')
        return request.render("repair_request.repair_request_template",
                              {'repair_request': repair_request, 'page_name': "view_details"})

    @http.route('/my/repair_requests/accept/<int:repair_id>', type='http', auth="user", website=True)
    def accept_quotation(self, repair_id, **kw):
        repair_request = request.env['repair_request.repair_request'].sudo().browse(repair_id)
        if repair_request.status == 'client_review':
            repair_request.sudo().accept_quotation()
        return request.redirect('/my/repair_requests')

    @http.route(['/my/repair_requests/view_quotation/<int:repair_id>'], type='http', auth="user", website=True)
    def view_quotation(self, repair_id, **kw):
        try:
            repair_request = request.env['repair_request.repair_request'].sudo().browse(repair_id)
            if not repair_request.exists() or not repair_request.quotation_id:
                logger.warning("Repair request does not exist or no quotation found")
                return request.redirect('/my/repair_requests')
            quotation = repair_request.quotation_id
            return request.render("repair_request.quotation_template", {
                'repair_request': repair_request,
                'quotation': quotation,
                'repair_id': repair_id,
                'page_name': "view_quotation"})
        except Exception as e:
            logger.error("Error in view_quotation: %s", str(e))
            return request.redirect('/my/repair_requests')



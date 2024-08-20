# -- coding: utf-8 --
from datetime import datetime

from odoo import http
from datetime import datetime
from odoo.addons.portal.controllers.portal import CustomerPortal as CustomerPortal
from odoo.http import request, route
from odoo.exceptions import UserError
from PIL import UnidentifiedImageError
import base64
import logging

logger = logging.getLogger(__name__)


class CustomerPortalHome(CustomerPortal):
    @http.route(['/my/repair_requests'], type='http', auth="user", website=True)
    def lists(self, **kw):
        repair_requests = request.env['repair_request.repair_request'].sudo().search(
            [('partner_id', '=', request.env.user.partner_id.id)], order='create_date desc')
        state_mapping = {
            "new": "New",
            "quotation": "In Progress",
            "client_review": "Quotation Review",
            "accepted": "Sales Order Confirmed",
            "cancel": "Cancelled",
        }
        return request.render("repair_request.repair_lists",
                              {'repair_requests': repair_requests, 'state_mapping': state_mapping,
                               'page_name': "repair_lists"})

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
        # Retrieve form data
        product_type = kw.get('product_type')
        description = kw.get('repair_request_description')
        repair_deadline = kw.get('repair_deadline')
        repair_image = request.httprequest.files.getlist('repair_image')

        # Initialize error dictionary
        errors = {}
        if not repair_image:
            errors["repair_image"] = "Please upload at least one image"

        if errors:
            return request.redirect('/my/create-request')

        # Try to save the repair request with images
        try:
            allowed_extensions = ["jpg", "jpeg", "png", "webp"]
            image_ids = []
            for image in repair_image:
                file_extension = image.filename.split(".")[-1].lower()
                if file_extension not in allowed_extensions:
                    raise UnidentifiedImageError("Invalid image type")
                encoded_image = base64.b64encode(image.read())
                attachment = request.env["ir.attachment"].sudo().create(
                    {
                        "name": image.filename,
                        "datas": encoded_image,
                        "res_model": "repair_request.repair_request",
                        "mimetype": image.content_type,
                    }
                )
                image_ids.append(attachment.id)
                logger.info("Image attached with ID: %s", attachment.id)

            # Parse the repair deadline correctly
            try:
                repair_deadline = datetime.strptime(repair_deadline, '%Y-%m-%dT%H:%M')
                logger.info("Parsed repair_deadline: %s", repair_deadline)
            except ValueError as e:
                errors["repair_deadline"] = "Invalid date format"
                logger.error("Invalid date format for repair_deadline: %s", e)
                return request.redirect('/my/create-request')

            request.env['repair_request.repair_request'].sudo().create(
                {
                    'product_type': product_type,
                    'client_email': request.env.user.email,
                    'description': description,
                    'repair_deadline': repair_deadline,
                    'repair_image': [(6, 0, image_ids)],
                    'partner_id': request.env.user.partner_id.id,
                })
            # Store success message in the session
            request.session['success_message'] = 'Repair request submitted successfully with images!'
        except UserError as e:
            # Handle known errors
            request.session['error_message'] = str(e)
        except Exception as e:
            # Handle unknown errors
            request.session['error_message'] = f"An unexpected error occurred: {e}"

        return request.redirect('/my/repair_requests')

    @http.route('/my/repair_requests/<int:repair_id>', type='http', auth="user", website=True)
    def view_repair_request(self, repair_id, **kw):
        repair_request = request.env['repair_request.repair_request'].sudo().browse(repair_id)
        if not repair_request.exists() or repair_request.partner_id.id != request.env.user.partner_id.id:
            return request.redirect('/my/repair_requests')
        logger.info("Repair request found with images: %s", repair_request.repair_image)
        images = []
        for attachment in repair_request.repair_image:
            try:
                image_data = attachment.datas.decode('utf-8')
                images.append({'id': attachment.id, 'data': image_data, 'name': attachment.name})
            except Exception as e:
                logger.error(f"Error reading image {attachment.id}: {e}")
        values = {
            "page_name": "view_details",
            "repair_request": repair_request,
            "images": images,
        }
        return request.render("repair_request.repair_request_template", values)

    @http.route(['/my/repair_requests/edit/<int:repair_id>'], type='http', auth="user", website=True)
    def edit_repair_request(self, repair_id, **kw):
        repair_request = request.env['repair_request.repair_request'].sudo().browse(repair_id)
        if not repair_request.exists() or repair_request.partner_id.id != request.env.user.partner_id.id:
            return request.redirect('/my/repair_requests')
        if repair_request.status not in ['new', 'quotation', 'client_review']:
            return request.redirect('/my/repair_requests')

        images = []
        for attachment in repair_request.repair_image:
            try:
                image_data = attachment.datas.decode('utf-8')
                images.append({'id': attachment.id, 'data': image_data, 'name': attachment.name})
            except Exception as e:
                logger.error(f"Error reading image {attachment.id}: {e}")

        values = {
            'page_name': 'edit_request',
            'repair_request': repair_request,
            'images': images,
        }
        return request.render("repair_request.edit_repair_request", values)

    @http.route(['/my/repair_requests/update/<int:repair_id>'], type='http', auth="user", methods=['POST'],
                website=True, csrf=True)
    def update_repair_request(self, repair_id, **kw):
        repair_request = request.env['repair_request.repair_request'].sudo().browse(repair_id)
        if not repair_request.exists() or repair_request.partner_id.id != request.env.user.partner_id.id:
            return request.redirect('/my/repair_requests')
        if repair_request.status not in ['new', 'quotation', 'client_review']:
            return request.redirect('/my/repair_requests')

        # Handle datetime conversion
        repair_deadline = kw.get('repair_deadline')
        if repair_deadline:
            try:
                dt = datetime.strptime(repair_deadline, '%Y-%m-%dT%H:%M')
                repair_deadline = dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                return request.render('repair_request.edit_repair_request', {
                    'error_message': 'Invalid date format',
                    'repair_request': repair_request,
                })

        values = {
            'product_type': kw.get('product_type'),
            'description': kw.get('repair_request_description'),
            'repair_deadline': repair_deadline,
        }

        # Handle image uploads
        uploaded_files = request.httprequest.files.getlist('repair_image')
        if uploaded_files:
            for upload in uploaded_files:
                file_content = upload.read()
                if file_content:
                    data = base64.b64encode(file_content)
                    attachment_vals = {
                        'name': upload.filename,
                        'datas': data,
                        'res_model': 'repair_request.repair_request',
                        'res_id': repair_id,
                    }
                    attachment = request.env['ir.attachment'].sudo().create(attachment_vals)
                    repair_request.write({'repair_image': [(4, attachment.id)]})

        # Handle image deletions
        for key, value in kw.items():
            if key.startswith('delete_image_') and value == 'on':
                image_id = int(key.split('_')[-1])
                repair_request.write({'repair_image': [(3, image_id)]})

        repair_request.write(values)
        return request.redirect('/my/repair_requests/%s' % repair_id)

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

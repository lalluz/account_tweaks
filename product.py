# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.osv import fields

from openerp.tools.translate import _


class product_template(osv.osv):

    _inherit = "product.template"

    _columns = {
        'property_analytic_account_income': fields.property (
            type='many2one',
            relation='account.analytic.account',
            string="Income Analytic Account",
        )
    }

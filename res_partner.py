# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.osv import fields

from openerp.tools.translate import _


class res_partner (osv.Model):

    _inherit = 'res.partner'

    def onchange_type (self, cr, uid, ids, is_company, context=None):
        res = super (res_partner, self).onchange_type (
            cr, uid, ids, is_company, context=context)

        if is_company:
            res['value'] = {'parent_id': None}

        return res
